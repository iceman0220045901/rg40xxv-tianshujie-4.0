# 天书劫 原味加强版 4.0 —— Anbernic RG40XXV 移植

把《金庸群侠传》MOD《天书劫 原味强化版 4.0》的 Windows 版引擎，移植到 Anbernic RG40XXV 掌机上跑起来。

仓库里放的是**移植这一侧的东西**：显示后端改动、性能补丁、音频/音量处理、Ports 入口、构建脚本和实测记录。游戏本体数据（`data/`、`pic/`、`font/`、`script/` 等）不在这里，需要自备。

## 现在能跑到什么程度

实测在 RG40XXV 真机（640×480 面板）：

| 场景 | 原版引擎直跑 | 移植后 |
|---|---|---|
| 标题页 | 14.8 fps | **37.4 fps** |
| 游戏内（客栈/城镇） | 7~8 fps | **29.8~30 fps** |
| 大地图 | 约 18 fps | **26.0~26.4 fps** |
| 读档列表 | — | 12 fps |

画面：1280×720 内部画布等比缩放到 640×360，上下各 60 px 黑边，居中。

功能：读档、存档、走动、对话、战斗、系统菜单、内置攻略、MIDI 音乐、音效、机身音量键、电源键待机唤醒、从 Ports 菜单启动。

## 基于什么

- **游戏数据**：MOD 作者 hervgui1987 GS 发布的《天书劫 原味强化版 4.0》Windows 版。
- **引擎**：该 MOD 自带的 `jysdl` 引擎源码（SDL2 分支），本仓库的补丁全部打在这份源码上，没有替换引擎结构。
- **SDL2**：用的是机器自带的 `libSDL2-2.0.so.0.12.0`（4,965,488 B）。实测过自编译 2.0.12 和系统里的 2.28.5，前者慢 8%、后者慢 4 倍，都否决了。
- **音频**：引擎自带的 BASS + BassMIDI，音色库走游戏数据自带的。
- **显示**：不用 SDL 的视频后端，自己写 `/dev/fb0` 直写，因为前端退出后 fb 是 32bpp/stride 2560，而 SDL 的 fbdev 后端吃不住这个模式。

## 硬件与环境

- Anbernic RG40XXV，Allwinner H700（Cortex-A53 ×4，1.512 GHz），973 MB 内存
- 系统：Ubuntu 22.04（Anbernic 魔改），kernel 4.9.170，glibc 2.35
- 面板 640×480；前端退出后 fb 为 `32bpp / stride 2560 / virtual 640×960 / RGB 16:8 8:8 0:8`
- 游戏装在根分区 `/roms/ports/jysdlbh`，Ports 菜单条目在 `/mnt/sdcard/Roms/PORTS/`

## 移植中真正难的地方

不是"编不过"，而是下面这几处，每一处都卡过：

| 问题 | 现象 | 怎么解决的 |
|---|---|---|
| fb 模式错配 | 前端退出后花屏、纵向条纹 | 前端在跑时 fb 是 16bpp，退到 Ports 后变 32bpp/stride 2560。改成引擎每 5 秒重新 `ioctl` 读 bpp/stride/RGB，一变就刷新内部参数，不再假设 16bpp |
| SDL2 版本 | 全屏 blit 慢到不可用 | 机上多份 libSDL2 实测，自带 2.0.12 比 2.28.5 快 4 倍；靠 `LD_LIBRARY_PATH` + `rpath $ORIGIN/lib` 优先加载 |
| 输出缩放 | 1280×720 → 640×360 每帧 8~11 ms | 精确 2:1 情形加 NEON 快路径（`vhaddq_u8` + `vuzp_u32`），误差 ≤1 色阶 |
| 每帧重画 | 游戏内 1405 次小 blit / 23 ms，占帧时间 48% | 给场景层函数套整屏缓存，镜头/朝向不变直接贴上一帧 |
| MIDI 无声 | 路径和文件都对，就是不出声 | 用了错误的解码入口 + 音色库开关没挂上 |
| 音量 | 一开就最大声，机身音量键无效 | `/etc/asound.conf` 的 `pcm.!default` 是 `type hooks`，把 `digital volume` 写死 63 且 `lock true`；改调可写的 `lineout volume`，并自己接住音量键 |
| Ports 菜单看不到 | 条目就是不出现 | 列表不读 `/mnt/mmc` 也不读 `config.json`，真实目录是 `/mnt/sdcard/Roms/PORTS`，每条是 `名字.sh` + `Imgs/名字.png` |
| 电源键待机 | 唤醒那一次按键又被当成新请求，"一亮就睡回去" | 用墙钟/单调时钟漂移判定区分"刚被唤醒"和"用户新按下"，加唤醒保护窗口 |

详细过程写在 `docs/` 里：

- `docs/01-性能优化-实测与决策.md` —— 每帧到底花在哪（LD_PRELOAD 探针实测）、NEON 缩放、SDL2 版本裁定、场景层缓存
- `docs/02-移植问题与解决办法.md` —— 显示、音频、音量、输入、入口、待机逐项的问题与思路

## 仓库结构

```
runtime/   直接拷到设备的运行时文件
  launch.sh            启动脚本（fb 守护、单实例、手柄映射、音量键）
  volkey.py            音量键 + 电源键待机守护
  jysdllua.gptk        gptokeyb 手柄映射
  config.json          Ports 配置
  天书劫4.0.sh         Ports 菜单入口（放 /mnt/sdcard/Roms/PORTS/）
scripts/   打在引擎源码上的补丁与构建脚本
  build.sh             引擎构建（-O2，四段编，末行 BUILD_OK）
  patch_fbmode.py      fb 模式自适应
  patch_fbperf2.py     blit 心跳与尺寸日志
  patch_scale2x.py     2:1 缩放 NEON 快路径
  patch_smapcache.py   场景层缓存（客栈/城镇）
  patch_mmapcache.py   场景层缓存（大地图）
  patch_vol.py         音乐/音效增益统一
docs/      实测与决策记录
```

## 怎么用

1. 准备引擎源码树（`jysdl/src`、`lua/src`、`shim`、`zlib` 等），把 `scripts/` 里的补丁按需执行。补丁都是纯 ASCII、幂等，重复跑不会重复插入，源码里会留标记宏（`JY_FB_SCALE2X_NEON` / `JY_SMAP_CACHE` / `JY_MMAP_CACHE`）。
2. `sh scripts/build.sh`，设备上约 25~28 秒，末行输出 `BUILD_OK`。
3. 把 `runtime/` 里的文件拷到 `/roms/ports/jysdlbh/`，`天书劫4.0.sh` 拷到 `/mnt/sdcard/Roms/PORTS/`，图标放 `Imgs/天书劫4.0.png`。
4. 从 Ports 菜单启动。

## 已知限制

- 读档列表仍是 12 fps（每帧 49 次 blit、56.7 ms，占 68%），缓存方案已评估未实施。
- 标题页 37.4 fps，静态层缓存预计能到 43~45 fps，同样未做。
- 游戏内开系统设置时有一处 Lua 崩溃（`menuItem[cur][3]` 对 nil 项取索引），根因已定位到 `ShowMenu2_new`，修复未做。
- 内置攻略的剧情变色依赖存档进度（`JY.GLTS`），空进度存档进去永远全白，属机制而非 bug。
- 标题页左上三行版本水印未处理。

## 说明

游戏本体、美术与剧情版权归原 MOD 作者与《金庸群侠传》相关权利人所有。这里只放移植层的代码与文档，不含游戏数据。
