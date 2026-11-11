# -*- coding: utf-8 -*-
# 把 patch_fbperf.py 里用到 clock_gettime 的计时改成 SDL_GetPerformanceCounter，
# 避免 aarch64 上缺 -lrt / _POSIX_C_SOURCE 导致的编译错误。
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "jysdl/src/sdlfun.c"
data = open(path, "rb").read()

reps = [
 (b'        struct timespec _a, _b; double _d;\r\n',
  b'        Uint64 _f, _a, _b; double _d;\r\n'),
 (b'        clock_gettime(CLOCK_MONOTONIC, &_a);\r\n',
  b'        _f = SDL_GetPerformanceFrequency();\r\n        _a = SDL_GetPerformanceCounter();\r\n'),
 (b'        clock_gettime(CLOCK_MONOTONIC, &_b);\r\n',
  b'        _b = SDL_GetPerformanceCounter();\r\n'),
 (b'        _d = (double)(_b.tv_sec - _a.tv_sec) * 1000.0 + (double)(_b.tv_nsec - _a.tv_nsec) / 1000000.0;\r\n',
  b'        _d = (double)(_b - _a) * 1000.0 / (double)_f;\r\n'),
]

for old, new in reps:
    if new in data:
        continue
    if old in data:
        data = data.replace(old, new, 1)
    else:
        alt = old.replace(b'\r\n', b'\n')
        if alt in data:
            data = data.replace(alt, new.replace(b'\r\n', b'\n'), 1)
        else:
            print('MISS:', old[:40])
            sys.exit(1)

open(path, 'wb').write(data)
print('patched: perf timing uses SDL counters')
