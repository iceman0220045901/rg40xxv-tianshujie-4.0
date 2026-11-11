import sys, os
MARK = b"JY_FB_SCALE2X_NEON"
INC_ANCHOR = b"#include <dirent.h>"
SCALE_ANCHOR = b"    if ((dstW < srcW || dstH < srcH) && g_FbXS0 != NULL && g_FbYS0 != NULL)"

INC_NEW = INC_ANCHOR + b"\n#include <arm_neon.h>"

BLOCK = b"""    /* ---- JY_FB_SCALE2X_NEON: exact 2:1 downscale fast path ---- */
    if (g_FbBytes == 4 && dstW > 0 && dstH > 0 &&
        srcW == (dstW << 1) && srcH == (dstH << 1) && spitch >= srcW * 4)
    {
        int yq;
        for (yq = 0; yq < dstH; yq++)
        {
            const unsigned int* ra = (const unsigned int*)(src + (size_t)(yq << 1) * spitch);
            const unsigned int* rb = (const unsigned int*)((const unsigned char*)ra + spitch);
            unsigned int* out = (unsigned int*)g_FbRow;
            int xq = 0;
            for (; xq + 1 < dstW; xq += 2)
            {
                uint8x16_t va = vld1q_u8((const uint8_t*)(ra + (xq << 1)));
                uint8x16_t vb = vld1q_u8((const uint8_t*)(rb + (xq << 1)));
                uint8x16_t vm = vhaddq_u8(va, vb);
                uint8x8_t lo = vget_low_u8(vm);
                uint8x8_t hi = vget_high_u8(vm);
                uint32x2x2_t zp = vuzp_u32(vreinterpret_u32_u8(lo), vreinterpret_u32_u8(hi));
                uint8x8_t rs = vhadd_u8(vreinterpret_u8_u32(zp.val[0]),
                                        vreinterpret_u8_u32(zp.val[1]));
                vst1_u32(out + xq, vreinterpret_u32_u8(rs));
            }
            if (xq < dstW)
            {
                unsigned int p0 = ra[xq << 1], p1 = ra[(xq << 1) + 1];
                unsigned int p2 = rb[xq << 1], p3 = rb[(xq << 1) + 1];
                unsigned int r = ((p0 >> 16 & 255u) + (p1 >> 16 & 255u) + (p2 >> 16 & 255u) + (p3 >> 16 & 255u)) >> 2;
                unsigned int g = ((p0 >> 8 & 255u) + (p1 >> 8 & 255u) + (p2 >> 8 & 255u) + (p3 >> 8 & 255u)) >> 2;
                unsigned int b = ((p0 & 255u) + (p1 & 255u) + (p2 & 255u) + (p3 & 255u)) >> 2;
                out[xq] = 0xFF000000u | (r << 16) | (g << 8) | b;
            }
            JY_FbStoreRow(g_FbMem + (size_t)(yq + offY) * g_FbStride + (size_t)offX * g_FbBytes,
                (unsigned int*)g_FbRow, dstW);
        }
        return 0;
    }

"""

def main(path):
    data = open(path, "rb").read()
    if MARK in data:
        print("ALREADY_PATCHED")
        return 0
    ni = data.count(INC_ANCHOR)
    ns = data.count(SCALE_ANCHOR)
    if ni != 1 or ns != 1:
        print("ANCHOR_FAIL inc=%d scale=%d" % (ni, ns))
        return 1
    data = data.replace(INC_ANCHOR, INC_NEW, 1)
    data = data.replace(SCALE_ANCHOR, BLOCK + SCALE_ANCHOR, 1)
    open(path, "wb").write(data)
    print("PATCHED ok size=%d" % len(data))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))