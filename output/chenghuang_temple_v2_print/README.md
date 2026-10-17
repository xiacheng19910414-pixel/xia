# 城隍庙 V2 · P1S＋AMS 四色浅浮雕

沿用确认的新版建筑与马善政毛笔匾额，实际尺寸 **100 × 72.314 × 4 mm**。背面平整，采用背贴磁片，**本版没有磁铁安装槽**。

## 直接下载与打印

优先下载 [P1S＋AMS 已切片 3MF](3mf/chenghuang_temple_v2_P1S_AMS_sliced.3mf)。GitHub 文件页点右上角 **Download raw file（下载原始文件）**，保存后在 Bambu Studio 选择“文件 → 打开项目”。文件包含真实模型、四个原位材料实体、四色分配、P1S 参数和已验证的切片路径。

1. 设备选 **Bambu Lab P1S / 0.4 mm 喷嘴**，耗材预设 **Generic PLA**，板材 **纹理 PEI**。
2. 准备炭黑、深靛蓝、朱红、米白四卷 PLA。发送打印时，把项目中的四种耗材对应到实际 AMS 槽位；槽位顺序可以不同。软件中的颜色不会把单卷耗材变成四色。
3. 保持原尺寸、原方向和分件位置：平背朝下，正面朝上，关闭支撑。不要将四个高度实体分别“落到平台”或拆开打印。
4. 查看切片预览后发送打印。改变耗材品牌、板材或喷嘴时，应选择对应预设并重新切片。

预设采用 0.2 mm 层高（首层也为 0.2 mm）、20 层、2 道墙、100% 直线填充、外墙 60 mm/s、顶面 40 mm/s。擦料塔在模型右侧；保留冲刷，尤其红色换米白时避免串色。实际色泽取决于耗材，屏幕色号仅用于材料识别。

## 四色与换色高度

| 材料编号 | 颜色 | 实体高度区间 | 打印层 |
|---|---|---|---|
| 1 | 炭黑 `#202329` | Z=0–1.6 mm | 1–8 |
| 2 | 深靛蓝 `#24355C` | Z=1.6–2.4 mm | 9–12 |
| 3 | 朱红 `#AF302B` | Z=2.4–3.2 mm | 13–16 |
| 4 | 米白 `#EAE0C9` | Z=3.2–4.0 mm | 17–20 |

AMS 已配置为自动换色，共三次。手动换色时，应打印完 Z=1.6、2.4、3.2 mm 后，在下一层开始前换料；对应下一层顶面高度分别为 1.8、2.6、3.4 mm。务必核对切片层号。

高层区域下方由前面的材料承托；最终显示蓝色、红色的位置分别在对应高度结束。四个实体保持共同原点，是同一次打印的材料区间，不是分别打印后胶粘的拼装件。

## 文件

- `3mf/chenghuang_temple_v2_P1S_AMS_sliced.3mf`：优先使用，Bambu Studio 原生导出，带切片路径；额外补入真实 STL 渲染的封面图。
- `3mf/chenghuang_temple_v2_P1S_AMS.3mf`：未切片的带四色材料分配和 P1S 参数的项目，可重新切片。
- `3mf/temple_v2_geometry.3mf`：OpenSCAD 实际导出的整体几何备份，不附四色材料分配。
- `stl/temple_v2_complete.stl`：完整单一封闭实体。STL 格式本身不带颜色。
- `stl/band_1_black.stl` 至 `band_4_ivory.stl`：四色高度区间实体，原点与坐标一致。
- `source/temple_v2.scad`：可直接导出的独立 SCAD；`source/masks.svg`、`visible.svg`：实际毫米矢量源。
- `preview/front_effect.png`、`relief_tilted.png`：真实 STL 的正面与轻倾斜效果图，未夸大厚度。
- `preview/front_four_colors.png`、`front_actual_size.pdf`、`dimensions_and_layers.png`：四色分区、1:1 尺寸校样和高度结构图。
- `preview/actual_sliced_paths.png`：真实 G-code 路径复核图，包含圆弧路径。
- `validation.json`、`slicing_validation.json`：几何、材料、真实切片与换色检查记录。
- `source/export_log.json`、`bambu_slice.log`：实际导出和切片命令日志。

## 实际验证与打印适配

使用 OpenSCAD 2021.01 实际导出 STL 和 3MF；使用 trimesh 检查尺寸、封闭性、法向、重复/退化面、连通性和体积，并比对实际截面。完整模型为一个连通实体；四色高度实体中存在多个有意保留的色岛，但下方有实体支承。

Bambu Studio **02.08.02.61** 实际成功导入、切片并原生导出；验证了 20 层、3 次换色、四色材料、模型尺寸、字形区域有效挤出路径，以及 Bambu 未修补或移除网格面。最终自动化测试 **34 项通过**；匾额最后一层路径覆盖约 **98.7%**，预计约 **1 小时 5 分钟、19.4 g**（含冲刷与擦料塔）。详情以 JSON 报告为准；这是软件验证，尚未进行实物试打印。

云端缺少可用 Wayland 图形显示，Bambu 的自动 GUI 缩略图生成失败；切片和工程导出成功，已用实际 STL 的 CPU 渲染补全封面。没有把效果图冒充切片截图。

为适应 100 mm 宽、0.4 mm 喷嘴，对已确认图稿的色块作约 0.12 mm 加粗、0.8 mm 圆整处理，简化针状末端；匾额的八处内部留白扩大到约 0.64 mm。保留马善政字体、共同基线、自然字形比例和从左到右“庙隍城”的传统排字，未镜像文字。圆弧笔尖与曲线边缘会自然收窄，实物精细程度仍受喷嘴和耗材影响。

## 再生成

在仓库根目录：

```bash
bash setup.sh
.venv/bin/python scripts/build_temple_v2.py
```

建筑、字体与适配规则分别在 `src/temple_v2_design.py`、`src/temple_v2_print.py`。字体随仓库提供，许可证见 `assets/fonts/mashanzheng/OFL.txt`。P1S 参数已保存在 `source/P1S_AMS_project_settings.json`，不依赖前次任务的临时下载目录。官方 Bambu 参数的来源和修改说明见 `source/profile_provenance.json`，上游 AGPL-3.0 许可证见仓库 `assets/licenses/BambuStudio-LICENSE.txt`。

若安装了 Bambu Studio，可额外运行：

```bash
.venv/bin/python scripts/slice_temple_v2.py --bambu /实际路径/bambu-studio --work-dir /tmp/temple-v2-slice
.venv/bin/python -m pytest -q
```

修改模型后，必须重新生成并重新切片；自动测试会检测过期源文件和过期切片项目。恢复云端的细节见仓库 `docs/bambu_p1s_v2.md`。
