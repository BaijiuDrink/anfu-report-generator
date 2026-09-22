# 安服报告工作台

面向 Windows 和主流桌面 Linux 的渗透测试漏洞整理与 Word 报告生成工具。桌面端使用 PySide6，重点解决漏洞录入、证据图片粘贴、项目归档和报告生成中的重复工作。

## 主要功能

- 专业工作台布局：漏洞列表与编辑区左右分栏，宽度可调整。
- 独立漏洞库：支持搜索、分类、预览、增删改，以及快速选择弹窗。
- 完整漏洞编辑：所有多行字段均有独立滚动条，整个表单也可纵向滚动。
- Word/WPS 图文粘贴：尽量保持文字与图片顺序，过滤空白候选并优先保留高清图片。
- 原图与预览分离：界面只显示缩略预览，DOCX 始终读取磁盘原图，不降低报告图片质量。
- 项目文件兼容：继续使用 `project_name` 和 `findings` JSON 结构，附件保存到 `<项目名>_attachments`。
- 报告生成：沿用现有报告内容、字段顺序和风险分组，生成前提示缺失或损坏的证据图片。
- 安全的编辑流程：切换漏洞、页面、项目或关闭程序时，对未保存内容提供保存、放弃和取消。

## 直接下载运行

普通用户无需安装 Python，可从 GitHub Releases 下载对应平台文件：

- Windows 10/11 x86_64：`安服报告生成工具.exe`
- Ubuntu、Debian、Kali、Fedora 等主流 Linux x86_64：`anfu-report-generator-x86_64.AppImage`
- 无法使用 AppImage/FUSE 时：`anfu-report-generator-linux-x86_64.tar.gz`

Linux 首次运行 AppImage 前执行一次 `chmod +x anfu-report-generator-x86_64.AppImage`，之后可直接双击或运行该文件。

## 源码环境要求

- Python 3.11 或更高版本
- Windows 10/11，或主流 x86_64 桌面 Linux
- Microsoft Word 或 WPS 不是运行必需项，仅在从文档复制图文证据时使用

## 安装运行

```powershell
git clone https://github.com/BaijiuDrink/anfu-report-generator.git
cd anfu-report-generator
python -m pip install -r requirements.txt
python gui_app.py
```

开发环境与测试工具：

```powershell
python -m pip install -r requirements-dev.txt
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -q
```

## 基本流程

1. 输入项目名称，新建漏洞或从漏洞库选择模板。
2. 填写地址、描述、验证结果、修复建议等内容。
3. 在“漏洞验证”中直接粘贴 Word/WPS 图文或单张、多张截图。
4. 保存项目为 JSON；证据图片会复制到配套附件目录并写入相对路径。
5. 点击“生成报告”输出 DOCX。缺失图片会先集中提示，不会静默丢失标记。

旧版本保存的项目 JSON 可直接打开。新版本保存的项目仍保留原字段与截图标记格式 `[截图: path]`。

## 本地打包

```powershell
python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm --clean "安服报告生成工具.spec"
```

Windows 生成文件位于 `dist/安服报告生成工具.exe`。Linux 在对应系统执行同一命令后生成 `dist/anfu-report-generator`，再运行 `bash packaging/build_appimage.sh` 可生成 AppImage。PyInstaller 使用官方 PySide6 hooks 收集 Qt 平台插件，漏洞库默认数据会一并打包。

推送 `v*` 标签后，GitHub Actions 会分别在 Windows 和 Ubuntu 22.04 上构建，并把 EXE、AppImage 和 Linux tar.gz 上传到对应 GitHub Release。

## 命令行说明

`report_generator.py` 作为兼容旧流程的命令行入口继续保留，但属于 legacy 功能。后续开发以桌面工作台为主，不再扩展 CLI。

## 后续开发备忘

- 项目首页和最近项目
- 自动保存与简单备份
- 报告模板和样式设置

## 数据与日志

- 项目文件：用户选择的 `.json` 路径
- 项目附件：项目文件旁的 `<项目名>_attachments` 目录
- 运行日志：`%LOCALAPPDATA%/BaijiuDrink/AnfuReportWorkbench/logs/application.log`

## License

MIT
