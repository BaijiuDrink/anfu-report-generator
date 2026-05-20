<p align="center">
  <img src="https://img.shields.io/badge/python-3.7+-blue.svg" alt="Python 3.7+">
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" alt="Windows">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
</p>

<h1 align="center">🔐 渗透测试报告生成工具</h1>
<p align="center"><strong>Pentest Report Generator</strong></p>

<p align="center">一站式渗透测试漏洞管理与 Word 报告生成工具，让安服报告编写效率翻倍。</p>

---

## ✨ 特性

- 🖥️ **图形化桌面应用** — 基于 tkinter 构建，直观的拖拽式操作体验
- ⚡ **批量录入** — 一个漏洞模板 + 多台主机，一键批量生成漏洞记录
- 📸 **截图粘贴** — Ctrl+V 一键粘贴剪贴板截图，自动嵌入报告
- 🎨 **专业排版** — 自动生成 A4 版面 Word 报告，封面 + 统计概览 + 逐条详情一步到位
- 🌐 **网络区域分组** — 按互联网 / 内网分组统计，风险等级颜色标记（严重 🔴 高危 🟠 中危 🟡 低危 🟢）
- 💾 **项目持久化** — 报告项目可保存为 JSON 配置，随时加载继续编辑
- ⌨️ **CLI 模式** — 同时支持命令行交互式流程，方便脚本集成

## 🚀 快速开始

### 环境要求

- **Python** 3.7 及以上
- **操作系统** Windows（截图粘贴依赖 `pywin32`）

### 安装

```bash
git clone https://github.com/your-org/pentest-report-generator.git
cd pentest-report-generator
pip install -r requirements.txt
```

### 运行

```bash
# 图形化界面（推荐）
python gui_app.py

# 命令行交互模式
python report_generator.py
```

## 📦 项目结构

```
安服报告生成/
├── gui_app.py                GUI 主程序（v2.0）
├── report_generator.py       CLI 命令行入口（v1.0）
├── report_builder.py         Word 报告构建引擎
├── vuln_manager.py           漏洞库 CRUD 管理
├── vuln_library/
│   └── default_vulns.json    默认漏洞模板库
├── output/                   报告输出目录
├── screenshots/              截图存储目录（运行时自动创建）
└── requirements.txt          依赖清单
```


## 🎯 使用场景

- ✅ 渗透测试完成后快速输出客户交付报告
- ✅ 等保测评 / 风险评估合规报告编写
- ✅ 安全团队内部漏洞知识库沉淀




