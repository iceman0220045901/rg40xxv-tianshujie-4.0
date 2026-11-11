#!/bin/sh
# 天书劫 4.0（原味强化版）RG40XXV —— Ports 菜单入口
# 游戏本体在根分区 /roms/ports/jysdlbh，显示/音频/输入都在那边的 launch.sh 处理。
# 这里刻意不 source PortMaster/control.txt：它是 bash 专用，而 dmenu_ln 用 sh 执行 .next，
# 两者混用会直接报语法错、游戏起不来。
export HOME=/root
GDIR=/roms/ports/jysdlbh
CUR_TTY=/dev/tty0
chmod 666 /dev/uinput 2>/dev/null
chmod 666 "$CUR_TTY" 2>/dev/null
printf "\033c" > "$CUR_TTY" 2>/dev/null
echo "Starting 天书劫 4.0 ..." > "$CUR_TTY" 2>/dev/null
exec sh "$GDIR/launch.sh"
