# BioFlow-CLI

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://python.org)

**[English Documentation](README.md)**

专业的生物信息学 TUI（终端用户界面）工作流工具，支持完整的中英文国际化。

## 功能特性

- **交互式 TUI** — 基于 `questionary` + `rich` 构建，提供优雅的终端交互体验
- **国际化支持** — 完整的中英文本地化；首次运行时选择语言，偏好保存至用户配置目录
- **环境管理器** — 一键检测和安装常用生物工具（FastQC、SAMtools、BWA、BLAST+、Trimmomatic），通过 Conda 管理
- **序列格式化** — 标准化 FASTA 文件，支持自定义行宽
- **模块化设计** — `env_manager`、`bio_tasks`、`i18n` 模块职责清晰分离

## 快速开始

### 安全安装（推荐）

```bash
# 下载安装脚本及其校验和
curl -LO https://github.com/woshinidad88/BioFlow-CLI/releases/latest/download/install.sh
curl -LO https://github.com/woshinidad88/BioFlow-CLI/releases/latest/download/install.sh.sha256

# 运行前验证完整性（平台特定）
# Linux：
sha256sum -c install.sh.sha256

# macOS：
shasum -a 256 -c install.sh.sha256

# Windows（PowerShell）：
# (Get-FileHash install.sh -Algorithm SHA256).Hash -eq (Get-Content install.sh.sha256).Split()[0]

# 如果验证失败，请勿继续 — 重新下载文件

# 运行安装程序（Linux/macOS）
bash install.sh
```

### 其他安装方式

```bash
# 克隆仓库
git clone https://github.com/woshinidad88/BioFlow-CLI.git
cd BioFlow-CLI

# 方式 A：使用安装脚本（不验证）
chmod +x install.sh && ./install.sh

# 方式 B：手动安装
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m bioflow.main
```

## 项目结构

```
BioFlow-CLI/
├── bioflow/
│   ├── __init__.py        # 包元数据
│   ├── main.py            # TUI 入口与主菜单
│   ├── i18n.py            # 国际化核心模块
│   ├── env_manager.py     # 生物工具检测与安装
│   ├── bio_tasks.py       # 序列格式化任务
│   └── locales/
│       ├── __init__.py    # 语言包注册
│       ├── en.py          # 英文字符串
│       └── zh.py          # 中文字符串
├── install.sh             # 双语安装脚本
├── pyproject.toml         # 构建配置
├── requirements.txt       # 依赖列表
├── LICENSE                # MIT 许可证
├── README.md              # 英文文档
└── README_CN.md           # 中文文档
```

## 使用说明

BioFlow-CLI 支持 **交互式 TUI 模式** 和 **非交互式 CLI 模式**。

### TUI 模式（交互式）

不带参数启动以进入交互式菜单：

```bash
bioflow
```

首次启动时，会提示您选择语言。选择结果会持久化保存，可随时通过设置菜单更改。

### CLI 模式（非交互式）

使用命令行参数进行自动化和脚本编写：

```bash
# 格式化 FASTA 序列
bioflow seq --input input.fasta --output output.fasta --width 80

# 列出生物工具安装状态
bioflow env --list

# 安装指定工具
bioflow env --install fastqc

# 静默模式（抑制进度消息）
bioflow --quiet seq --input input.fasta

# JSON 输出（便于解析）
bioflow --json seq --input input.fasta
```

#### 退出码

| 代码 | 含义 |
|---|---|
| `0` | 成功 |
| `1` | 运行时错误（如：无效的 FASTA 格式、安装失败） |
| `2` | 参数错误（如：文件不存在、无效参数） |
| `3` | 依赖缺失（如：Conda 未安装） |

#### 输出流

- **stdout**：结果和数据（用于管道传输）
- **stderr**：进度消息、警告和错误

### 配置文件位置

| 操作系统 | 路径 |
|---|---|
| macOS | `~/Library/Application Support/bioflow/config.json` |
| Linux | `~/.config/bioflow/config.json`（或 `$XDG_CONFIG_HOME/bioflow/`） |
| Windows | `%APPDATA%\bioflow\config.json` |

### 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `BIOFLOW_LARGE_FILE_MB` | FASTA 大文件警告阈值（MB） | `500` |

### 主菜单

| 操作 | 说明 |
|---|---|
| **[环境] 安装生物工具** | 检测并通过 Conda 安装生物信息学工具 |
| **[序列] 格式化处理** | 标准化 FASTA 文件格式 |
| **[设置] 切换语言** | 在中文和英文之间切换 |
| **[退出] 退出程序** | 退出应用 |

## 环境要求

- Python 3.9+
- [Conda](https://docs.conda.io/)（用于安装生物工具）

## 许可证

本项目基于 MIT 许可证开源。详见 [LICENSE](LICENSE)。
