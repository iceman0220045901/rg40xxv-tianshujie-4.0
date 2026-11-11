#!/usr/bin/env python3
# 天书劫 4.0 RG40XXV —— 机身按键守护：音量键 + 电源键待机
#
# 背景
#   跑 Ports 游戏时前端 muos2.bin 已经退出，正常情况下由它处理的两件事没人做了：
#     1) 音量键 —— 而且 /etc/asound.conf 的 hook 每次打开音频设备都会把
#        "digital volume" 写成 63 并 lock（再写报 Operation not permitted），
#        所以游戏一出声就是满音量。真正可写的是 "lineout volume"(numid=3, 0..31)。
#     2) 电源键短按待机 —— 系统原本的做法就是 /mnt/vendor/ctrl/pwr_new.sh，
#        本质是 `echo -n mem > /sys/power/state`，唤醒源是 PMIC 上的电源键。
#
# 本进程读 /dev/input/eventN（不 grab，和 gptokeyb 共存）：
#   KEY_VOLUMEDOWN(114) / KEY_VOLUMEUP(115) -> 改 lineout volume，步长 2
#   KEY_POWER(116) 短按（< 2s）-> 待机；长按不管，交给硬件/PMIC
#
# 唤醒消抖：机器挂起时单调时钟停走、墙钟照走，靠两者的漂移就能认出"刚被唤醒"。
# 不这么做的话，用户按下电源键唤醒的那一次按键会被当成新的待机请求，
# 结果就是"一亮就睡回去"（已实测踩过）。
#
# 注：本机 RTC(pcf8563) 的 wakealarm 叫不醒 mem，已验证失效，故不用它兜底。
#
# 用法：volkey.py [初始音量0-31]
# 当前音量存 /tmp/jy4_dac_vol，退出再进保持。

import fcntl
import os
import select
import struct
import subprocess
import sys
import time

VOL_FILE = "/tmp/jy4_dac_vol"
LOG_FILE = "/tmp/jy4_vol.log"
MINV, MAXV, DEFV = 0, 31, 18
STEP = 2
KEY_VOL_DOWN = 114
KEY_VOL_UP = 115
KEY_POWER = 116
LONG_PRESS = 2.0          # 超过这个时长算长按，不触发待机
WAKE_GUARD = 6.0          # 刚被唤醒后这段时间一律忽略电源键
DRIFT_MIN = 2.0           # 墙钟领先单调时钟多少秒算"挂起过"
SUSPEND_STATE = "/sys/power/state"


def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass


def read_vol():
    try:
        return max(MINV, min(MAXV, int(open(VOL_FILE).read().strip())))
    except Exception:
        return DEFV


def apply_vol(v):
    v = max(MINV, min(MAXV, v))
    try:
        with open(VOL_FILE, "w") as f:
            f.write(str(v))
    except Exception:
        pass
    subprocess.call(["amixer", "-c", "0", "cset", "numid=3", str(v)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log("vol=%d" % v)
    return v


def do_suspend():
    log("suspend")
    try:
        with open(SUSPEND_STATE, "w") as f:
            f.write("mem")
    except Exception as e:
        log("suspend fail: %s" % e)
        return time.monotonic()
    t = time.monotonic()
    log("resumed")
    return t


def _ioc(ev, ln):
    return (2 << 30) | (ln << 16) | (0x45 << 8) | (0x20 + ev)


def node_keys(fd):
    buf = bytearray(96)
    try:
        fcntl.ioctl(fd, _ioc(1, 96), buf)
    except Exception:
        return set()
    return set(i for i in range(96 * 8) if buf[i // 8] & (1 << (i % 8)))


def drain(nodes):
    for n in nodes:
        try:
            while os.read(n["fd"], 24 * 64):
                pass
        except Exception:
            pass


def main():
    cur = read_vol()
    if len(sys.argv) > 1:
        try:
            cur = int(sys.argv[1])
        except Exception:
            pass
    cur = apply_vol(cur)
    log("start cur=%d" % cur)

    nodes = []
    for p in sorted(os.listdir("/dev/input")):
        if not p.startswith("event"):
            continue
        path = "/dev/input/" + p
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        except Exception as e:
            log("open fail %s %s" % (path, e))
            continue
        keys = node_keys(fd)
        if (KEY_VOL_UP in keys) or (KEY_POWER in keys):
            nodes.append({"path": path, "fd": fd, "keys": keys})
            log("listen %s vol=%d power=%d" % (
                path, KEY_VOL_UP in keys, KEY_POWER in keys))
        else:
            os.close(fd)

    if not nodes:
        log("no usable node")
        return 1

    ignore_power_until = 0.0
    pressed_at = {}
    prev_mono = time.monotonic()
    prev_wall = time.time()

    while True:
        try:
            ready, _, _ = select.select([n["fd"] for n in nodes], [], [], 1.0)
        except Exception:
            return 0

        # 先判断"刚才是不是挂起过"：墙钟在走、单调时钟不走，两者差就是睡眠时长
        now = time.monotonic()
        wall = time.time()
        drift = (wall - prev_wall) - (now - prev_mono)
        prev_mono, prev_wall = now, wall
        if drift > DRIFT_MIN:
            ignore_power_until = now + WAKE_GUARD
            pressed_at.clear()
            log("resume detected sleep=%.1fs, power ignored %.0fs" % (drift, WAKE_GUARD))
            drain(nodes)

        if not ready:
            continue

        for n in nodes:
            if n["fd"] not in ready:
                continue
            try:
                data = os.read(n["fd"], 24 * 64)
            except Exception:
                continue
            for off in range(0, len(data) - 23, 24):
                _s, _u, etype, code, value = struct.unpack("llHHi", data[off:off + 24])
                if etype != 1:
                    continue

                if code in (KEY_VOL_UP, KEY_VOL_DOWN) and value == 1:
                    if code == KEY_VOL_UP:
                        cur = apply_vol(cur + STEP)
                    else:
                        cur = apply_vol(cur - STEP)
                    continue

                if code != KEY_POWER:
                    continue

                if value == 1:
                    pressed_at[n["path"]] = now
                elif value == 0:
                    t0 = pressed_at.pop(n["path"], None)
                    if t0 is None:
                        continue
                    dur = now - t0
                    if now < ignore_power_until:
                        log("power ignored (wake guard) dur=%.2fs" % dur)
                        continue
                    if dur < LONG_PRESS:
                        wake_t = do_suspend()
                        ignore_power_until = wake_t + WAKE_GUARD
                        pressed_at.clear()
                        drain(nodes)
                    else:
                        log("power long press %.1fs, ignored" % dur)
    return 0


if __name__ == "__main__":
    sys.exit(main())
