# -*- coding: utf-8 -*-
# Volume gain patch (ASCII-only payload so it is safe on a GBK source file):
#   JY_VOL_GAIN  music gain (default 2.5 -> 20 becomes 50)
#   JY_SFX_GAIN  sfx gain   (default 4.0 -> 10 becomes 40)
# cap 100, never writes back the globals, so in-game volume stays adjustable.
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "jysdl/src/sdlfun.c"
data = open(path, "rb").read()

ANCHOR = b'extern int g_MusicVolume;\r\n'
HELPER = (
 b'extern int g_MusicVolume;\r\n'
 b'\r\n'
 b'/* volume gain: stock 0-100 values are almost inaudible on a handheld speaker; */\r\n'
 b'/* scale by a factor, cap at 100, never write back (in-game setting stays usable). */\r\n'
 b'static int JY_VolEff(int base, const char* gain)\r\n'
 b'{\r\n'
 b'    double k = 2.5;\r\n'
 b'    int v;\r\n'
 b'    if (gain != NULL && gain[0] != 0) { k = atof(gain); }\r\n'
 b'    if (k <= 0.0) { k = 1.0; }\r\n'
 b'    v = (int)((double)base * k);\r\n'
 b'    if (v > 100) { v = 100; }\r\n'
 b'    if (v < 0) { v = 0; }\r\n'
 b'    return v;\r\n'
 b'}\r\n'
)

OLD_M = (
 b'    { const char* _mv = getenv("JY_MUSIC_VOL"); if (_mv != NULL && _mv[0] != 0) { g_MusicVolume = atoi(_mv); }\r\n'
 b'      BASS_ChannelSetAttribute(currentMusic, BASS_ATTRIB_VOL, (float)(g_MusicVolume / 100.0)); }\r\n'
)
NEW_M = (
 b'    { int _vol = JY_VolEff(g_MusicVolume, getenv("JY_VOL_GAIN"));\r\n'
 b'      BASS_ChannelSetAttribute(currentMusic, BASS_ATTRIB_VOL, (float)(_vol / 100.0)); }\r\n'
)

OLD_S = b'        BASS_ChannelSetAttribute(ch, BASS_ATTRIB_VOL, (float)(g_SoundVolume / 100.0));\r\n'
NEW_S = (
 b'        BASS_ChannelSetAttribute(ch, BASS_ATTRIB_VOL,\r\n'
 b'            (float)(JY_VolEff(g_SoundVolume, getenv("JY_SFX_GAIN")) / 100.0));\r\n'
)

if b'JY_VolEff' in data:
    print('already patched')
    sys.exit(0)

for old, new in ((ANCHOR, HELPER), (OLD_M, NEW_M), (OLD_S, NEW_S)):
    if old in data:
        data = data.replace(old, new, 1)
        continue
    alt_old = old.replace(b'\r\n', b'\n')
    if alt_old in data:
        data = data.replace(alt_old, new.replace(b'\r\n', b'\n'), 1)
        continue
    print('MISS:', old[:50])
    sys.exit(1)

open(path, 'wb').write(data)
print('patched: volume gain OK')
