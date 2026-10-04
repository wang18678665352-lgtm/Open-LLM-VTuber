# Open-LLM-VTuber Qt6 启动器

一个用 **Qt6 / PySide6** 重写的原生 Windows 图形化启动器，用来替代仓库根目录里早期的
tkinter 版 `launcher.py`。界面风格致敬秋葉 aaaki 的绘世启动器：深色主题、左侧导航、
卡片式布局，但完全使用系统原生窗口与原生控件，可打包成单文件 exe 分发。

> 本启动器是社区自制工具，与 Open-LLM-VTuber 官方无关。
>
> 旧的 tkinter 版本仍保留在根目录 `launcher.py` 中作为历史参考（`启动器.bat` 已不再调用它）。

## 功能

| 页面 | 内容 |
| --- | --- |
| 一键启动 | 启停 `run_server.py`、实时彩色控制台、`--verbose` / `--hf_mirror` / 自动打开浏览器开关、自动滚动与清空 |
| 高级选项 | 修改 `conf.yaml` 的监听地址与端口（自动备份）、6 个快捷打开入口、环境信息面板、托盘行为开关 |
| 版本管理 | 当前分支 / 最新提交 / 远程领先落后状态、`git fetch` 检查更新、一键更新（stash → pull + 子模块 → 同步配置 → `uv sync`） |
| 疑难解答 | 8 项环境一键扫描（Python 版本、uv、关键依赖、配置文件、前端子模块、Live2D 模型、ASR 模型、端口占用）、安装依赖、修复子模块 |
| 关于 | 版本信息、仓库与文档链接 |

其他特性：

- 深色渐变主题：窗口背景、侧边栏、卡片、按钮均为渐变或半透明质感，蓝紫强调色；
- 全部图标都是 `launcher_qt/core/icons.py` 里用 QPainter 现场绘制的**矢量图标**，
  没有外部图片依赖，可随主题换色、任意缩放不糊；
- 主视觉卡片（hero）带投影与光晕，启动按钮在运行/停止时切换蓝→红渐变与光晕颜色；
- 实时控制台按日志级别着色（TRACE/DEBUG/INFO/SUCCESS/WARNING/ERROR），最多保留 6000 行；
- 深色原生标题栏（DWM immersive dark mode）与 Win11 圆角；
- 系统托盘：最小化到托盘、托盘菜单启停服务器，关闭窗口时若服务器仍在运行会先确认；
- 单实例：重复启动只会唤起已有窗口；
- 高 DPI 友好（PassThrough 舍入，125% 缩放下不发虚）。

界面尺寸：默认 **1120 × 740**，最小 980 × 660；左侧导航宽 240。

## 运行

三种方式，任选其一：

1. **打包后的 exe**（推荐给最终用户）
   把 `dist/Open-LLM-VTuber-Launcher.exe` 放到项目根目录（与 `run_server.py` 同级）后双击。
   启动器会以自身所在目录为起点向上查找 `run_server.py` / `pyproject.toml` 来定位项目根目录，
   也可以用 `--root D:\path\to\project` 或环境变量 `LLV_LAUNCHER_ROOT` 显式指定。
   它不会自带 Python 依赖，运行时仍需要项目自己的 `.venv`（或可用的 `uv`）来启动服务器。

2. **批处理**：双击根目录的 `启动器.bat`（优先用 exe，其次用 `.venv-launcher`）。

3. **命令行（开发）**：

   ```bat
   .venv-launcher\Scripts\python.exe -m launcher_qt
   .venv-launcher\Scripts\python.exe run_launcher.py
   ```

### 命令行参数

```text
--root DIR          指定项目根目录（默认自动探测）
--selftest          离屏构建全部页面并自检后退出（CI / 打包验证）
--screenshot DIR    离屏渲染每个页面并保存 PNG 到 DIR
```

## 打包单文件 exe

首次准备构建环境（与项目自身的 `.venv` 隔离，可以用更新的 Python）：

```bat
uv venv .venv-launcher --python 3.13
uv pip install --python .venv-launcher\Scripts\python.exe pyside6-essentials pyinstaller pillow ruamel.yaml
```

然后：

```bat
build_launcher.bat                  :: 双击即可，单文件 exe
build_launcher.bat --onedir         :: 目录模式（启动更快）
build_launcher.bat --clean          :: 先清理 build/ 与 dist/
build_launcher.bat --console        :: 保留控制台窗口，排错用
build_launcher.bat --no-verify      :: 跳过构建后的离屏自检
```

脚本会：检查依赖 → 缺少图标时从 `frontend/favicon.ico` 生成多尺寸 `app.ico` →
调用 PyInstaller（`--onefile --windowed`、图标、`--add-data` 资源、
补充 `ruamel.yaml` 隐藏导入、排除用不到的 Qt 模块以减小体积）→
用 `--screenshot` 离屏渲染全部页面做一次自检。

产物：`dist/Open-LLM-VTuber-Launcher.exe`（约 40–60 MB，取决于 Qt 版本）。

## 目录结构

```text
run_launcher.py             打包入口（绝对导入，供 PyInstaller 用）
launcher_qt/
├── __init__.py             应用名称 / 版本 / 链接常量
├── __main__.py             命令行入口（--root / --selftest / --screenshot）
├── app.py                  主窗口：侧边栏 + 页面堆栈 + 托盘 + 单实例
├── assets/app.ico          应用图标（由 frontend/favicon.ico 生成）
├── core/
│   ├── paths.py            项目根目录探测、路径常量、打包态判断
│   ├── config.py           conf.yaml 读写（ruamel 优先，保留注释）、启动器设置
│   ├── icons.py            用 QPainter 绘制的矢量图标集（无需图片资源）
│   ├── theme.py            调色板、全局 QSS、深色原生标题栏
│   ├── text.py             ANSI 清理与日志级别识别
│   ├── server.py           run_server.py 子进程管理与就绪后打开浏览器
│   ├── runner.py           后台命令序列执行器（更新 / 安装依赖）
│   └── system.py           环境探测、git 信息、8 项扫描
├── widgets/
│   ├── common.py           卡片 / 页面标题 / 按钮 / 药丸 / 阴影光晕等通用组件
│   ├── console.py          按级别着色的控制台视图
│   └── task_dialog.py      耗时任务对话框
└── pages/                  home / advanced / version / troubleshoot / about
scripts/build_launcher.py   打包脚本
```

## 写入范围

启动器**不会修改项目源码**，只有两类写操作：

- `conf.yaml`：修改监听地址 / 端口时写入（首次写入前自动备份为 `conf.yaml.launcher.bak`，
  使用 ruamel.yaml 保留注释；缺少该库时退化为定点正则替换）；
- `launcher_settings.json`：保存启动器自己的选项（详细日志 / HF 镜像 / 自动打开浏览器 /
  自动滚动 / 最小化到托盘）。

## 与 git 远程仓库的关系

本仓库的远程配置遵循标准 fork 工作流：

```text
origin    https://github.com/wang18678665352-lgtm/Open-LLM-VTuber.git   （个人 fork）
upstream  https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git        （官方仓库）
```

- 同步官方更新：`git fetch upstream` → `git merge upstream/main`（或 `git rebase upstream/main`）；
- 推送自己的改动：`git push origin main`；
- 启动器「版本管理」页里的“远程状态”比较的是 `HEAD...@{upstream}`，也就是当前分支
  `main` 所跟踪的远程分支 `origin/main`（你的 fork），用来提示本地是否还有未推送的提交。
