# 本次实际执行结果

验证日期：2026-10-16。此处记录当前云机器的实测结果；不代表未来环境已发布或恢复验证，也未进行切片和实物打印。

## 软件和网络

- OS：Debian GNU/Linux 13，x86_64。
- Python：3.12.14；项目 `.venv` 已创建。
- OpenSCAD：2021.01，Debian 软件包 2021.01-8，路径 `/usr/bin/openscad`；本次已预装，直接复用，没有重复进行系统安装。
- HTTPS 只读请求：`https://pypi.org/simple/numpy/` 与 `https://deb.debian.org/debian/` 均为 200。Python 依赖实际下载和安装成功，没有关闭 TLS 或签名验证。
- `bash setup.sh` 完整执行成功，并重复执行成功；`pip check`：No broken requirements found。

| Python 包 | 安装版本 |
|---|---|
| numpy | 2.5.4 |
| trimesh | 5.1.1 |
| Pillow | 12.3.0 |
| opencv-python-headless | 5.0.0.93 |
| shapely | 2.2.0 |
| svgpathtools | 1.8.0 |
| scipy | 1.18.1 |
| matplotlib | 3.11.2 |
| pytest | 9.1.1 |

`requirements.txt` 固定以上包及实际安装的间接依赖版本。numpy/scipy 的这些版本要求 Python >=3.12，因此脚本会提前检查解释器版本。

## 实际几何检查

执行 `.venv/bin/python scripts/build_sample.py`，通过 OpenSCAD CLI 分别导出 6 个 STL 和 1 个 3MF。真实 CLI 参数和逐件检查保存在 `output/validation.json`。未使用占位 STL，也未用拼接三角网格替代整体 CSG 并集。

| 部件 | 尺寸 mm | 实测体积 mm³ | 封闭性 | 连通实体 |
|---|---|---|---|---|
| 底板 | 100×70×2 | 14000 | 通过 | 1 |
| 红色装饰 | 45×30×1 | 1350 | 通过 | 1 |
| 黄色装饰 | 45×30×1 | 1350 | 通过 | 1 |
| 绿色装饰 | 45×30×1 | 1350 | 通过 | 1 |
| 蓝色装饰 | 45×30×1 | 1350 | 通过 | 1 |
| 整体 STL | 100×70×3 | 19400 | 通过 | 1 |
| 整体 3MF | 100×70×3 | 19400 | 通过 | 1 |

每项均检查包围盒与预期位置、正体积与解析计算值、法向一致性、退化面及重复面；最终文件无退化面、无重复面。整体 76 个三角形。STL 按 mm 解释，3MF 单位在 XML 中重新确认是 millimeter；3MF 经 ZIP 完整性检查并解析真实三角面后用 trimesh 验证。此 3MF 只交付单实体几何，不含四色材料映射或切片器配置。

PNG 由真实 STL 向上三角面生成正交俯视图，并验证红、黄、绿、蓝每种颜色均有足够的实际像素。曾发现 Matplotlib 三维绘制对大底板和小装饰面的深度排序导致遮挡，最终改为正确的俯视投影并重新导出、重新测试。

## 自动化测试

最终执行 `.venv/bin/python -m pytest -q`：**18 passed**，无失败、无跳过、无预期失败。

覆盖实际 OpenSCAD 导出、默认尺寸和解析体积、各色件坐标与无体积重叠、各件体积之和等于整体体积、3MF 重新解析、PNG 四色可见、非默认 80×60×5 mm 模型；还确认开口、退化面、重复面、反向实体、空网格、零厚度、非有限坐标、错误尺寸/体积、多个分离实体及无效参数被拒绝。图像依赖测试实际调用 Pillow、OpenCV、Shapely、SciPy 与 svgpathtools，完成内存图片到轮廓/多边形及 SVG 路径检查。

另行执行 `.venv/bin/python scripts/check_mesh.py output/stl/assembly.stl --size 100 70 3 --volume 19400` 成功。

## 恢复配置与剩余边界

已保存 Codex 环境配置草稿的 `install_script` 与 `start_skill`：前者调用仓库 `setup.sh`，后者记录诊断、恢复、测试、输出路径和使用现有检出的规则。草稿保存不会自动发布；用户需在环境设置中查看、保存并发布。当前未验证发布后新任务的恢复。

代码与轻量最终产物准备本地 Git 暂存；不包含 `.venv`、缓存和原始私人图片，不向远端推送。后续图片仍需逐图建模，不能从一张图片保证自动重建任意物体的完整深度与背面。
