#!/bin/sh
# RG40XXV 上原生编译 jysdllua（16bpp fbdev 版）
set -e
cd "$(dirname "$0")"
B=$(pwd)
OUT=$B/obj
rm -rf "$OUT"; mkdir -p "$OUT/zlib" "$OUT/mz" "$OUT/lua" "$OUT/game"

INC="-I$B/jysdl/src -I$B/lua/src -I$B/shim -I$B/zlib -I$B/zlib/contrib/minizip \
-I/usr/include/SDL2 -I$B/inc -I$B/jysdl/Bass/include -I$B/jysdl/tinypot/include"
CFLAGS="-O2 -w -std=gnu99 -Wno-implicit-function-declaration -Wno-implicit-int -Wno-int-conversion -Wno-incompatible-pointer-types"
# 注：-O3 -mcpu=cortex-a53 实测无收益（游戏内 21.1 对 20.6 fps，在噪声内），
#     且老代码对严格别名敏感，故保持 -O2。缩放热点已由 sdlfun.c 的 NEON 路径解决。

echo "== zlib =="
for f in "$B"/zlib/*.c; do
  n=$(basename "$f" .c)
  gcc $CFLAGS $INC -c -o "$OUT/zlib/$n.o" "$f"
done

echo "== minizip + shim =="
for n in unzip zip ioapi; do
  gcc $CFLAGS $INC -c -o "$OUT/mz/$n.o" "$B/zlib/contrib/minizip/$n.c"
done
for f in "$B"/shim/*.c; do
  n=$(basename "$f" .c)
  gcc $CFLAGS $INC -c -o "$OUT/mz/$n.o" "$f"
done

echo "== lua 5.2.4 =="
for f in "$B"/lua/src/*.c; do
  n=$(basename "$f" .c)
  case "$n" in lua|luac) continue;; esac
  gcc $CFLAGS $INC -c -o "$OUT/lua/$n.o" "$f"
done

echo "== engine =="
for n in charset jymain luafun mainmap piccache sdlfun SDL2_rotozoom; do
  gcc $CFLAGS $INC -c -o "$OUT/game/$n.o" "$B/jysdl/src/$n.c"
done

echo "== link =="
gcc -O2 -o "$B/jysdllua" "$OUT"/zlib/*.o "$OUT"/mz/*.o "$OUT"/lua/*.o "$OUT"/game/*.o \
  -L"$B/lib" -lSDL2 -lSDL2_image -lSDL2_ttf -lbass -lbassmidi \
  -Wl,-rpath,'$ORIGIN/lib' -lc -lpthread -lm -ldl

ls -l "$B/jysdllua"
echo BUILD_OK
