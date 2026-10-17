# P1S V2 再生成与云端验证记录

本次采用确认后的 V2 建筑设计与 Ma Shan Zheng 毛笔字。原确认稿位于 `output/chenghuang_temple_v2`，最终打印版独立存放于 `output/chenghuang_temple_v2_print`，未覆盖旧文件。

## 必要环境

`bash setup.sh` 恢复 OpenSCAD、Python 虚拟环境和锁定的依赖。模型及四色项目构建使用仓库内保存的 P1S 展开参数 JSON，因此新任务不需要下载 Bambu Studio 即可生成未切片 3MF。

再次验证原生切片需要 Bambu Studio。此次实际下载官方 Ubuntu 24.04 AppImage：

https://github.com/bambulab/BambuStudio/releases/download/v02.08.02.61/BambuStudio_ubuntu24.04-v02.08.02.61-20260820225108.AppImage

下载到 `/tmp`，用 `--appimage-extract` 解包；未提交二进制、虚拟环境或缓存。完整官方参数的来源与 SHA256 保存在最终输出的 `source/profile_provenance.json`，原机型、工艺、耗材展开值也保存在 `source`。

本次没有 root 权限。AppImage 依赖的 WebKit 库未预装，于是从允许访问的 Debian 官方仓库下载 `.deb`，使用 `dpkg-deb -x` 解压至 `/tmp/bambu-libs`，通过 `LD_LIBRARY_PATH` 临时加载。使用了 `libwebkit2gtk-4.1-0`、`libjavascriptcoregtk-4.1-0`、`libharfbuzz-icu0`、`libmanette-0.2-0`、`libhyphen0`、`libhidapi-hidraw0`。未修改系统库或全局 apt 源。

系统默认的 snapshot.debian.org 源返回网络代理 403；单独使用 `/tmp` 中的 apt 配置访问允许的 `https://deb.debian.org/debian trixie main`，完成库下载。无需用户修改当前网络权限。图形显示不可用只影响自动缩略图，已切片项目用实际模型 CPU 渲染补上封面。

## 生成、原生切片与检查

```bash
bash setup.sh
.venv/bin/python scripts/build_temple_v2.py
LD_LIBRARY_PATH=/tmp/bambu-libs/usr/lib/x86_64-linux-gnu:/tmp/squashfs-root/bin \
  .venv/bin/python scripts/slice_temple_v2.py \
  --bambu /tmp/squashfs-root/bin/bambu-studio --work-dir /tmp/temple-v2-slice
.venv/bin/python -m pytest -q
```

临时库路径仅适用于此次解包位置；新环境先检查库是否已存在。用户在电脑上的 Bambu Studio 中直接打开交付 3MF 即可，不需要执行这些命令。

切片程序同时检查 Bambu 的 `result.json` 和实际 G-code；该 CLI 发生某些错误时仍可能返回进程退出码 0，因此不能仅看退出码。程序验证所有 20 个层高，T1/T2/T3 的切换高度，匾额有效路径覆盖，以及原生导出后每种材料的网格和体积；不允许 Bambu 静默修补网格。

最终项目保留完整几何和打印配置，可重新切片；初层/全部层高固定 0.2 mm。`filament_map` 在新 Bambu 格式中表示物理喷头映射，P1S 四种材料均映射单喷头 1；AMS 实际槽位在发送打印时由用户按耗材颜色对应。
