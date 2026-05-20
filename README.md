<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" alt="Windows">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/github/actions/workflow/status/BaijiuDrink/anfu-report-generator/ci.yml" alt="CI Status">
</p>

<h1 align="center">🔐 安服报告生成工具</h1>
<p align="center"><strong>Pentest Report Generator</strong></p>

<p align="center">漏洞管理与 Word 报告自动生成工具，大幅提升安全服务报告编写效率。</p>

---

## ✨ 特性

- ⚡ **批量录入** — 一个漏洞模板 + 多台主机，一键批量生成漏洞记录
- 📸 **截图粘贴** — 支持 Ctrl+V 快速粘贴剪贴板截图，自动嵌入报告
- 🎨 **专业 Word 报告** — 自动生成 A4 格式报告，包含封面、统计概览、风险分布、逐条详情
- 🌐 **网络区域分组** — 按「互联网 / 内网」分组统计，风险等级颜色标识
- 💾 **项目持久化** — 支持保存/加载 JSON 项目文件，随时继续编辑
- ⌨️ **CLI + GUI** — 同时支持图形界面和命令行模式

## 🚀 快速开始

### 环境要求

- **Python** 3.11 或更高版本
- **操作系统**：Windows（推荐 Windows 10/11）

### 安装运行

```bash
# 1. 克隆项目
git clone https://github.com/BaijiuDrink/anfu-report-generator.git
cd anfu-report-generator

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动程序
python gui_app.py