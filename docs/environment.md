# 环境恢复说明

当前系统 Debian GNU/Linux 13 (amd64)。OpenSCAD 系统包已经存在，安装版本 2021.01-8，命令版本 2021.01。Python 3.12.14。安装脚本只有在 OpenSCAD 缺失时才尝试系统包安装，不重复修改现有系统。

恢复步骤：进入实际仓库根目录，运行 `bash setup.sh`。默认虚拟环境在 `.venv/`；可用 `PYTHON_BIN=python3.12 bash setup.sh` 指定解释器。虚拟环境不能跨路径/系统任意搬移；从干净仓库运行脚本创建新的环境。已有但损坏的虚拟环境应先移到备份位置，再运行脚本。

必需网络：Python 软件包索引和文件下载（通常 pypi.org、files.pythonhosted.org）；若需要系统安装，还需系统配置的软件源（Debian 常见 deb.debian.org、security.debian.org）。GitHub 访问使用平台现有 HTTPS 认证。无需第三方 API 密钥。不关闭 TLS、包签名或校验。

本次对 pypi.org 与 deb.debian.org 进行了 HTTPS 只读检查，均返回 200；依赖实际下载成功。网络仍受环境域名策略约束，不能据此推断任意网站可用。若后续环境安装被阻止，在 Codex 环境设置中补充失败日志对应的必要域名，保留已有名单；不要直接打开所有域名。没有 root/免密 sudo 的机器缺 OpenSCAD 时，请管理员在系统镜像中预装它。

Codex 环境的安装脚本：

```sh
set -eu
cd /workspace/xia
bash setup.sh
```

启动说明：使用已有检出；除非用户明确要求不要创建 worktree。进入 `/workspace/xia`，运行 `.venv/bin/python scripts/doctor.py`；缺依赖时运行 `bash setup.sh`。按需运行生成命令和 pytest；无常驻服务。环境设置草稿的保存不等同于已发布；需在设置中保存并发布才能供未来任务使用，首次新任务仍应运行诊断和测试。

城隍庙项目追加依赖：networkx（实际 STL 截面分析）、系统字体包 fonts-noto-cjk（将真实中文匾额转成多边形）。setup.sh 已检查字体；requirements.txt 已固定 networkx 版本。直接打开已导出的 temple.scad 不再需要字体。
