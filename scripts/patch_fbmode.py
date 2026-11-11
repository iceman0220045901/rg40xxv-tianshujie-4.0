# -*- coding: utf-8 -*-
# 给 sdlfun.c 的 fbdev 后端加“运行时重新读取 /dev/fb0 模式”的能力。
# 背景：muos 前端(muos2.bin)退出后，DE 会把 fb0 从 16bpp/640x480 切成
#       32bpp/640x960(双缓冲)，引擎若还按 16bpp 写就是花屏。
# 做法：每 5 秒（已有 blit 心跳处）重新 GET vinfo/finfo，变了就更新
#       bpp / stride / RGB 位域，写帧继续按新格式走。
import io, sys, os

path = sys.argv[1] if len(sys.argv) > 1 else "jysdl/src/sdlfun.c"
data = open(path, "rb").read()

OLD = (
b'      { long _t = (long)time(NULL); if (_t - _t0 >= 5) { _t0 = _t;\r\n'
b'        sprintf(_b, "blit hb n=%d src=%dx%d dst=%dx%d off=%d,%d", _cnt, srcW, srcH, dstW, dstH, offX, offY); JY_FbLog(_b); } } }'
)

NEW = (
b'      { long _t = (long)time(NULL); if (_t - _t0 >= 5) { _t0 = _t;\r\n'
b'        sprintf(_b, "blit hb n=%d src=%dx%d dst=%dx%d off=%d,%d", _cnt, srcW, srcH, dstW, dstH, offX, offY); JY_FbLog(_b);\r\n'
b'        { struct fb_var_screeninfo _vi; struct fb_fix_screeninfo _fi;\r\n'
b'          if (g_FbFd >= 0 && ioctl(g_FbFd, FBIOGET_VSCREENINFO, &_vi) == 0 &&\r\n'
b'              ioctl(g_FbFd, FBIOGET_FSCREENINFO, &_fi) == 0)\r\n'
b'          {\r\n'
b'            int _bpp = _vi.bits_per_pixel; int _by = _bpp / 8;\r\n'
b'            if (_by < 2 || _by > 4) { _by = 4; _bpp = 32; }\r\n'
b'            if (_bpp != g_FbBpp || _by != g_FbBytes || _fi.line_length != g_FbStride ||\r\n'
b'                _vi.red.offset != g_PixRPos || _vi.green.offset != g_PixGPos ||\r\n'
b'                _vi.blue.offset != g_PixBPos)\r\n'
b'            {\r\n'
b'              g_FbBpp = _bpp; g_FbBytes = _by; g_FbStride = _fi.line_length;\r\n'
b'              g_PixRPos = _vi.red.offset;   g_PixRLen = _vi.red.length;\r\n'
b'              g_PixGPos = _vi.green.offset; g_PixGLen = _vi.green.length;\r\n'
b'              g_PixBPos = _vi.blue.offset;  g_PixBLen = _vi.blue.length;\r\n'
b'              sprintf(_b, "fbdev: mode changed bpp=%d stride=%d rgb=%d/%d %d/%d %d/%d",\r\n'
b'                g_FbBpp, g_FbStride, g_PixRPos, g_PixRLen, g_PixGPos, g_PixGLen, g_PixBPos, g_PixBLen);\r\n'
b'              JY_FbLog(_b);\r\n'
b'            }\r\n'
b'          } } } } }'
)

# 兼容 LF 版本
OLD_LF = OLD.replace(b"\r\n", b"\n")
NEW_LF = NEW.replace(b"\r\n", b"\n")

if NEW in data or NEW_LF in data:
    print("already patched")
    sys.exit(0)

if OLD in data:
    data = data.replace(OLD, NEW, 1)
elif OLD_LF in data:
    data = data.replace(OLD_LF, NEW_LF, 1)
else:
    print("PATTERN NOT FOUND")
    sys.exit(1)

open(path, "wb").write(data)
print("patched: fbmode recheck OK")
