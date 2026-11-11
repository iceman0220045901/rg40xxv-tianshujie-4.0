#!/bin/sh
# =============================================================================
# 天书劫 4.0 原味强化版 —— Anbernic RG40XXV（640×480 / 32bpp）Ports 启动脚本
# -----------------------------------------------------------------------------
# 显示：直写 /dev/fb0（运行时自动重读 bpp/stride/RGB，前端退出后变 32bpp 也能画对）
#       内部渲染面 JY_SURF_W/H，输出按 JY_FB_SCALE 缩到 640×360，上下 60 px 纯黑
#       换画布只需改下面两行（960×540 更快，1280×720 排版最稳）
# 输入：gptokeyb 把掌机手柄翻译成键盘事件（引擎只认 SDL 键盘事件）
# 音频：音量 0-100 由 set.ini 决定（默认 20/10），这里只按倍数放大到听得见：
#       JY_VOL_GAIN=2.5（音乐） JY_SFX_GAIN=4（音效），游戏内设置依然可调
# 立绘：固定框 JY_HEAD_FIT（1280×720 面用 146，960×540 面用 110）
# =============================================================================
cd "$(dirname "$0")" || exit 1
PORTDIR=$PWD
ulimit -n 4096 2>/dev/null

# 前端 muOS 的调度约定：dmenu_ln 循环跑 muos2.bin，muos2.bin 退出后若存在
# /tmp/.next 就执行它，然后再回循环。
#
# 只有「从 SSH / 命令行直接起脚本、而前端还占着屏」时，才需要让前端先退出再由
# /tmp/.next 把我们拉起来（这时 /dev/fb0 才归我们）。
# 从 Ports 菜单启动时，muos2.bin 本身就是我们的父进程，前端会自己让位，此时
# 千万不能再写 .next / 杀前端，否则会被 dmenu_ln 再拉一次、变成双开或直接不启动。
FROM_FRONT=0
_jy4p=$PPID
_jy4i=0
while [ "$_jy4i" -lt 6 ]; do
    _jy4c=$(cat /proc/$_jy4p/comm 2>/dev/null)
    case "$_jy4c" in
        *muos*|*dmenu*|*MainUI*) FROM_FRONT=1 ;;
    esac
    _jy4p=$(awk '/^PPid:/ {print $2}' /proc/$_jy4p/status 2>/dev/null)
    [ -z "$_jy4p" ] && break
    if [ "$_jy4p" = "1" ] || [ "$_jy4p" = "0" ]; then break; fi
    _jy4i=$(( _jy4i + 1 ))
done
unset _jy4p _jy4i _jy4c

if [ "$FROM_FRONT" = "0" ] && [ ! -f /tmp/jy4_handoff ] && pidof muos2.bin > /dev/null 2>&1; then
    printf '#!/bin/sh\ntouch /tmp/jy4_handoff\nexec sh %s/launch.sh\n' "$PORTDIR" > /tmp/.next
    chmod +x /tmp/.next
    kill -TERM $(pidof muos2.bin) 2>/dev/null
    exit 0
fi

export LD_LIBRARY_PATH="$PORTDIR/lib:/usr/lib/aarch64-linux-gnu:/usr/lib:"
if [ -f ./gamecontrollerdb.txt ]; then
    export SDL_GAMECONTROLLERCONFIG_FILE="$PORTDIR/gamecontrollerdb.txt"
fi

# 4.0 的 set.ini 默认 CONFIG.MP3 = 1，会让脚本去找并不存在的 gameNN.mp3 -> 无声
if [ -f ./set.ini ] && ! grep -q "CONFIG.MP3 *= *0" ./set.ini 2>/dev/null; then
    sed -i 's/CONFIG\.MP3 *= *1/CONFIG.MP3 = 0/' ./set.ini 2>/dev/null
fi

# ---- 显示 ----
export JY_FBDEV=1
export JY_SURF_W=1280
export JY_SURF_H=720
export JY_FB_SCALE=0.5
export JY_FB_MASK=000000

# ---- 音量（倍数放大，不改写 set.ini）----
export JY_VOL_GAIN=2.5
export JY_SFX_GAIN=4
# 硬件音量：asound.conf 的 hook 每次开设备都把 "digital volume" 顶到 63 并锁死，
# 所以游戏一出声就是满的。真正可写的是 "lineout volume"(numid=3, 0..31)，
# 交给下面的 volkey.py 独占管理，这里只给它一个起始值（越小越轻）。
export JY_DAC_VOL=18

# ---- 立绘 ----
export JY_HEAD_FIT=146
export JY_HEAD_MAX=0

# ---- 单实例守卫：上一局残留的引擎 / gptokeyb / 音量守护先清掉，
#      否则两次启动会叠在一起抢 /dev/fb0，画面会闪 ----
[ -f /tmp/jy4_volkey.pid ] && kill -9 "$(cat /tmp/jy4_volkey.pid 2>/dev/null)" 2>/dev/null
for _p in $(pidof jysdllua 2>/dev/null); do kill -9 "$_p" 2>/dev/null; done
for _p in $(pidof gptokeyb 2>/dev/null); do kill -9 "$_p" 2>/dev/null; done
unset _p
sleep 1

# ---- 音量键（前端退出后没人处理音量键，自己顶一个）----
VOLKEY_PID=""
if [ -f ./volkey.py ]; then
    python3 ./volkey.py "$JY_DAC_VOL" > /tmp/jy4_vol.out 2>&1 &
    VOLKEY_PID=$!
    echo "$VOLKEY_PID" > /tmp/jy4_volkey.pid
fi

# ---- 输入 ----
if [ -x ./gptokeyb ] && [ -f ./jysdllua.gptk ]; then
    ./gptokeyb -k "jysdllua" -c "./jysdllua.gptk" > /tmp/jysdlbh_gptk.log 2>&1 &
    GPTOKEYB_PID=$!
    sleep 1
fi

run_game() {
    START_TS=$(date +%s)
    stdbuf -oL ./jysdllua > /tmp/jysdlbh.log 2>&1
    CODE=$?
    ELAPSED=$(( $(date +%s) - START_TS ))
    echo "$(date +%T) exit code=$CODE elapsed=${ELAPSED}s" >> /tmp/jysdlbh_diag.log
}

run_game
if [ "$ELAPSED" -lt 15 ]; then
    echo "$(date +%T) fast exit (${ELAPSED}s), retrying once" >> /tmp/jysdlbh_diag.log
    sleep 2
    run_game
fi

[ -n "$GPTOKEYB_PID" ] && kill -9 $GPTOKEYB_PID 2>/dev/null
[ -n "$VOLKEY_PID" ] && kill -9 $VOLKEY_PID 2>/dev/null
rm -f /tmp/jy4_volkey.pid
# 清掉交接标记，下次从前端/SSH 启动还能再走一次 .next 流程
rm -f /tmp/jy4_handoff
exit 0
