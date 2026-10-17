> 当前打印版：[城隍庙 V2 · 毛笔匾额 · P1S＋AMS](output/chenghuang_temple_v2_print/README.md)。提供实际导出、上色并切片验证的 3MF、完整 STL、四色高度实体及可编辑源文件。原外观确认稿和旧版保留。

# 可重复使用的 FDM 3D 打印建模项目

将图片放入 `input/`，然后告诉 Codex：“参考这张图，做成宽___、高___、总厚___毫米，颜色___，按___分件，并生成可打印文件。”不需要自己写代码。请尽量给出底板厚度、凸起高度、磁铁尺寸及喷嘴直径。

这是用于后续由 Codex 分析图片、编写参数化模型并验证的工程基础；当前自带的程序生成四色测试冰箱贴，不是任意图片自动还原三维物体的转换器。单张图片优先做轮廓挤出、平面分色或浅浮雕；遮挡、背面与真实深度需要说明或采用明确的假设。

## 一次安装 / 新任务恢复

在仓库根目录执行：

```bash
bash setup.sh
.venv/bin/python scripts/build_sample.py
.venv/bin/python -m pytest -q
```

`setup.sh` 可重复执行，复用已有 OpenSCAD 和虚拟环境，按 `requirements.txt` 的固定版本安装全部 Python 依赖并检查冲突。已实测 Debian 13、Python 3.12、OpenSCAD 2021.01。支持 Python >=3.12；其他 Python/系统版本仍需现场验证。新机器若缺 OpenSCAD，会尝试通过 apt-get（root 或免密 sudo）安装；若无权限则明确失败，需管理员预装 `openscad` 和匹配的 `python3-venv`。本环境已预装 OpenSCAD，所以本次没有执行系统安装。

在 Codex 环境设置的安装脚本中填写：

```bash
set -eu
cd /workspace/xia
bash setup.sh
```

恢复后没有需要常驻运行的服务。按需使用 `.venv/bin/python`；不要依赖先前任务的 shell 激活状态。详细恢复和网络说明见 [docs/environment.md](docs/environment.md)。

## 已提供的测试件

默认外形 **100×70×3 mm**，底板 **2 mm**，装饰层 **1 mm**。四个 45×30 mm 矩形彩色区域，边距 4 mm、区域间隔 2 mm；底板共用蓝色，总计四种材料颜色。

| 文件 | 内容 | 装配 Z 范围 |
|---|---|---|
| `output/stl/base.stl` | 蓝色底板，100×70×2 | 0–2 mm |
| `output/stl/red.stl` | 左上红色装饰，45×30×1 | 2–3 mm |
| `output/stl/yellow.stl` | 右上黄色装饰，45×30×1 | 2–3 mm |
| `output/stl/green.stl` | 左下绿色装饰，45×30×1 | 2–3 mm |
| `output/stl/blue.stl` | 右下蓝色装饰，45×30×1 | 2–3 mm |
| `output/stl/assembly.stl` | 全部布尔并集，单一封闭实体 | 0–3 mm |

- 参数化源文件：`src/magnet.scad`；本次输出的独立可编辑源文件：`output/magnet.scad`。
- 颜色/尺寸/坐标清单：`output/assembly.json`；几何检查与真实导出命令：`output/validation.json`。
- 预览：`output/preview/magnet.png`，由实际 STL 三角网格通过 Matplotlib 生成，不需要桌面或 Xvfb。
- `output/3mf/assembly.3mf`：OpenSCAD 实际导出的单实体毫米几何，已重新解析验证。它不包含四材料映射、打印机配置或切片设置。
- STL 不存颜色与单位；切片时选 mm。多材料切片请把底板和四装饰 STL **作为一个对象的多个部件共同导入，保留坐标**，按清单指定材料；不要再叠加 `assembly.stl`。
- 分开打印胶粘时，装饰件在切片器中单独“放到平台”（Z 减 2 mm），保持 1 mm 厚；打印后按预览粘到实心底板上。本示例无定位卡扣、无磁铁孔，可背面粘磁性片。需要嵌磁铁时先提供直径和厚度。

推荐 PLA、0.4 mm 喷嘴、0.2 mm 层高、平放打印，几何无悬挑，通常无需支撑。装饰区处于同一高度，单喷嘴简单按层换色不能实现同层四种颜色；应使用多材料设备或分件胶粘。尚未进行切片或实物试打印。

## 改尺寸 / 验证其他模型

```bash
.venv/bin/python scripts/build_sample.py --width 80 --height 60 --base 3 --decor 2 --output output/custom
.venv/bin/python scripts/check_mesh.py output/stl/assembly.stl --size 100 70 3 --volume 19400
.venv/bin/python scripts/doctor.py
```

修改 `src/magnet.scad` 可调整区域布局；宽、高、底板和装饰厚度建议使用命令行参数。生成程序实际调用 OpenSCAD，禁止空文件或只生成预览冒充实体。默认完整导出包含 PNG 和 3MF；`--no-extras` 可以跳过它们，但不会宣称未执行的可选检查通过。

## 文件组织

```text
input/             用户参考图片（默认不纳入 Git）
output/stl/        可打印整体和分件
output/3mf/        已验证的几何 3MF
output/preview/    由网格生成的预览
src/               可编辑 SCAD 与通用几何验证器
scripts/           生成、检查及环境诊断命令
tests/            实际导出、参数变化与坏网格拒绝测试
docs/             环境恢复及建模流程说明
```

不会提交虚拟环境与缓存。示例最终产物体积小，随代码保留便于直接下载；后续复杂模型请控制产物大小。精确环境和测试执行结果见 [docs/validation.md](docs/validation.md)。

## 城隍庙四色按高度换色冰箱贴

新建筑模型位于 `output/chenghuang_temple/`，为参考图简化的 100 mm 宽异形浅浮雕；详见该目录的 `README.md`。恢复依赖后实际重新生成：

```bash
.venv/bin/python scripts/build_temple.py
.venv/bin/python scripts/render_temple.py
.venv/bin/python -m pytest -q
```

匾额需要 Noto Sans CJK Bold 中文字体，`setup.sh` 会检查并在缺失且有安装权限时通过 apt 安装 `fonts-noto-cjk`。独立 `source/temple.scad` 已将字形转成真实多边形，直接用 OpenSCAD 导出时不依赖字体。
