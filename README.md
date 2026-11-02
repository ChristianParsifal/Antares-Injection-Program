# Antares Injection Program

> 面向 Windows 的 Codex 与 Claude Code API 配置工具。支持直接输入兼容中转站的 API 基础地址和 API Key，并将配置写入对应的 CLI、Codex 配置文件以及 Claude Desktop 官方第三方推理策略。

[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D4)](https://www.microsoft.com/windows)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-Tkinter-2C2C2C)](https://docs.python.org/3/library/tkinter.html)

> 项目当前面向 Windows x64。仓库未附带真实 API Key，也不会在测试中连接第三方中转站。

## 目录

- [项目简介](#项目简介)
- [主要功能](#主要功能)
- [程序构成](#程序构成)
- [兼容性与工作方式](#兼容性与工作方式)
- [快速开始](#快速开始)
- [从源码运行](#从源码运行)
- [构建 Windows EXE](#构建-windows-exe)
- [测试](#测试)
- [配置细节](#配置细节)
- [安全与隐私](#安全与隐私)
- [常见问题](#常见问题)
- [官方文档](#官方文档)
- [项目状态](#项目状态)

## 项目简介

Antares Intelligent 是一个 Windows 桌面配置工具，用于简化以下配置流程：

- 为 Codex CLI 配置 OpenAI Responses API 兼容线路。
- 为 Claude Code CLI 配置 Anthropic Messages API 兼容线路。
- 为支持官方 Third-Party Inference / Gateway 的 Claude Desktop 写入 Windows 用户策略。
- 检测 Node.js、npm 和 CLI 是否可用。
- 在缺少依赖时使用项目内置的 Node.js / Git 安装包辅助安装 CLI。

它不是 API 代理服务器，也不会转换 OpenAI Chat Completions 与 Responses API，更不会把不兼容的接口自动转换为 Anthropic Messages API。中转站本身必须实现目标客户端需要的协议。

## 主要功能

### 通用线路输入

- “线路”栏支持直接输入自定义 URL。
- 原有四条内置线路仍作为下拉预设保留。
- 支持 HTTPS、HTTP、本地域名、端口和路径前缀。
- 自动处理 Codex 与 Claude 的基础路径差异。
- 拒绝账号密码、空格、控制字符、查询参数和 URL 片段。
- 保存或获取模型前先进行地址校验，校验失败不会写入配置或发起网络请求。

### Codex

- 写入 Codex 的 `api_client` provider。
- 使用 `responses` 协议配置。
- 保留已有 `config.toml` 中的其它设置。
- 支持 `CODEX_HOME` 指定的配置目录。
- 保存前创建带时间戳的配置备份。
- 保留原有模型检测、配置检测和 CLI 安装流程。

### Claude Code 与 Claude Desktop

- CLI 使用 `ANTHROPIC_BASE_URL`、模型变量和用户环境变量配置。
- Desktop 使用官方 Windows 用户策略：
  `HKCU\SOFTWARE\Policies\Claude`。
- 支持 `x-api-key` 与 `bearer` 两种认证方式。
- 桌面端、CLI 和模型列表请求使用同一认证选择。
- 自动清理另一种认证方式的旧凭据，避免旧 Token 覆盖新配置。
- 保留无关的 Claude 策略值。
- 检测机器级策略、bootstrap、OIDC 和 credential helper 冲突。

### 安全和可靠性

- 模型列表请求不跟随 HTTP 重定向，避免 API Key 被发送到跳转目标。
- 写入失败时尝试恢复桌面策略、配置文件和用户环境变量。
- Windows 注册表策略写入前生成恢复备份。
- 对无法解析的 Codex TOML 不进行覆盖写入。
- 测试使用模拟网络、临时文件和模拟注册表，不修改真实客户端配置。

### 双语界面与辅助安装

- 支持简体中文和 English 界面。
- 支持检测 Node.js、npm 和对应 CLI。
- 缺少 Node.js 或 Git 时，可解压项目内置安装包到运行目录。
- 支持通过 npm 安装 Codex CLI 或 Claude Code CLI。
- 提供官方桌面客户端下载入口。

## 程序构成

项目采用 Python 单文件 Tkinter 应用，主要组成如下：

```text
AntaresIntelligentTool/
├─ AntaresIntelligentTool.py          # 主程序、界面、配置写入和 CLI 安装逻辑
├─ AntaresIntelligentTool.spec        # PyInstaller 打包配置
├─ requirements.txt                   # Pillow、PyInstaller 版本依赖
├─ README.md                          # 项目文档
├─ test_configuration.py              # URL、模型请求、Codex 和 ProfileTab 测试
├─ test_desktop_configuration.py      # Claude Desktop 策略、回滚和认证测试
├─ test_gui.py                         # Tk 界面、语言切换和布局测试
├─ test_executable.py                 # 打包 EXE 启动与关闭测试
├─ assets/
│  ├─ logo.png / logo.ico              # 应用图标
│  └─ installers/                      # 内置 Node.js / Git 安装包
├─ build/                              # PyInstaller 构建中间文件
└─ dist/                               # PyInstaller 输出目录
```

### 运行时配置位置

| 用途 | 默认位置 |
| --- | --- |
| Codex 配置 | `%USERPROFILE%\.codex\config.toml` |
| Codex 自定义目录 | `CODEX_HOME\config.toml` |
| Claude Desktop 用户策略 | `HKCU\SOFTWARE\Policies\Claude` |
| 配置备份和运行时文件 | `%LOCALAPPDATA%\APIClientTool\` |
| CLI 环境变量 | 当前用户环境变量，以及当前进程环境 |

## 兼容性与工作方式

### Codex 线路

中转站需要支持：

- OpenAI Responses API。
- 流式输出。
- Codex 所需的工具调用能力。
- 模型 ID 与站点实际可用模型一致。

地址处理规则：

```text
https://relay.example          → https://relay.example/v1
https://relay.example/openai  → https://relay.example/openai
https://relay.example/openai/v1 → 保持原路径
```

只支持 `/chat/completions` 的服务不能直接用于 Codex。

### Claude Code / Claude Desktop 线路

中转站需要支持：

- Anthropic Messages API。
- 流式输出。
- Claude Code 或 Claude Desktop 所需的工具调用能力。
- 站点实际支持的模型 ID。

地址处理规则：

```text
https://relay.example       → 保持根地址
https://relay.example/v1    → 移除末尾 /v1，由客户端追加 API 路径
https://relay.example/anthropic/v1 → https://relay.example/anthropic
```

只提供 OpenAI 格式接口的站点不能直接用于 Claude Code。

### 模型列表

“获取模型”会请求兼容客户端的模型列表接口，但并非所有中转站都实现该接口。获取失败时，可以手工输入站点实际支持的模型 ID 后保存。

模型列表请求成功，仅代表列表接口可访问，不代表聊天、流式输出和工具调用已经通过真实验证。

## 快速开始

### 使用已发布 EXE

1. 从 GitHub Releases 下载 `AntaresIntelligentTool.exe`。
2. 运行程序并选择 **Codex** 或 **Claude Code** 标签页。
3. 在“线路”中粘贴中转站提供的 API 基础地址。
4. 填写 API Key。
5. 选择认证方式（Claude 使用 `x-api-key` 或 `bearer` 时）。
6. 点击“获取模型”，或手工填写模型 ID。
7. 点击“保存配置”。
8. 完全退出并重新打开目标客户端或终端。

Claude Desktop 还需要在登录页选择第三方推理模式。不同客户端版本的界面可能略有差异。

### 地址填写示例

```text
# Codex 常见基础地址
https://relay.example
https://relay.example/openai/v1

# Claude 常见基础地址
https://relay.example/anthropic
https://relay.example/anthropic/v1
```

不要填写以下类型的地址：

```text
https://user:password@relay.example       # 含账号密码
https://relay.example?key=value           # 含查询参数
https://relay.example/v1/responses        # 单次 API 请求路径
https://relay.example/v1/messages         # 单次 API 请求路径
```

## 从源码运行

### 环境要求

- Windows 10/11 x64。
- Python 3.11 或更高版本，建议 Python 3.12。
- 可访问 Python 包索引的网络环境，仅安装依赖时需要。

### 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 启动程序

```powershell
python AntaresIntelligentTool.py
```

程序启动后，按照[快速开始](#快速开始)中的步骤填写线路和 Key。

## 构建 Windows EXE

项目使用 PyInstaller 的 `.spec` 文件打包，并将 `assets` 目录一并放入程序包：

```powershell
python -m PyInstaller --noconfirm AntaresIntelligentTool.spec
```

产物位于：

```text
dist\AntaresIntelligentTool.exe
```

该构建包含图标和项目内置的 Node.js / Git 安装资源。发布前建议在干净的 Windows 用户环境中启动一次 EXE，并确认不需要管理员权限即可完成预期流程。

## 测试

运行离线配置测试：

```powershell
python test_configuration.py
python test_desktop_configuration.py
python test_gui.py
```

构建 EXE 后，运行启动检查：

```powershell
python test_executable.py
```

测试覆盖：

- URL 规范化和非法地址拒绝。
- Codex TOML 写入、嵌套设置保留和备份。
- Claude Desktop 策略值、模型列表和无关配置保留。
- `x-api-key` / `bearer` 认证切换。
- 旧认证变量清理。
- 环境变量或策略写入失败后的回滚。
- HTTP 重定向凭据保护。
- 自定义 URL、模型加载和语言切换。
- GUI 布局以及打包 EXE 的启动响应。

测试不会：

- 使用真实 API Key。
- 连接真实中转站。
- 安装真实 CLI。
- 修改真实注册表、Codex 配置或 Claude 配置。

## 配置细节

### Codex

程序会配置以下内容：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_API_BASE`
- `OPENAI_MODEL`
- `%USERPROFILE%\.codex\config.toml` 中的 `api_client` provider

已有 TOML 无法解析时，程序不会覆盖原文件。设置 `CODEX_HOME` 后，配置文件会写入该目录。

### Claude Code

默认使用：

- `ANTHROPIC_API_KEY`
- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_MODEL`

选择 `bearer` 时，程序改用 `ANTHROPIC_AUTH_TOKEN`，并清理旧的 `ANTHROPIC_API_KEY`，避免两套认证同时存在。

如果检测到以下第三方推理环境变量已启用，程序会拒绝继续写入，避免多个后端配置互相覆盖：

- `CLAUDE_CODE_USE_BEDROCK`
- `CLAUDE_CODE_USE_VERTEX`
- `CLAUDE_CODE_USE_FOUNDRY`

### Claude Desktop

程序写入官方 Windows 用户策略中的第三方 Gateway 配置，包括：

- Gateway 基础地址。
- 静态 API Key。
- 认证方式。
- 默认模型列表。
- 第三方推理提供商标记。

机器级策略（`HKLM`）可能覆盖用户级策略。如果检测到机器级策略、bootstrap URL、OIDC 或 credential helper 冲突，程序会停止桌面端写入并提示处理方式。

策略备份默认保存到：

```text
%LOCALAPPDATA%\APIClientTool\backups\
```

备份可能包含旧 API Key。请勿将备份文件提交到公开仓库或上传到公共网盘。

## 安全与隐私

- API Key 只用于写入目标客户端配置和请求模型列表。
- 模型列表请求使用 HTTPS 时，建议优先使用 HTTPS 中转站地址。
- 程序不会把 API Key 写入日志或 README。
- 模型列表请求禁用重定向，避免凭据被带到其它主机。
- 配置备份可能包含旧 Key，备份目录应按敏感配置管理。
- 请不要把含有 API Key 的截图、日志、注册表导出文件或配置备份提交到 GitHub。
- 当前项目没有对中转站进行实际推理质量、数据留存和隐私政策审计；使用前请自行评估服务商。

## 常见问题

### 点击“获取模型”失败怎么办？

模型列表接口并非所有中转站都实现。请确认 URL 是 API 基础地址、认证方式正确，并尝试直接填写服务商提供的模型 ID 后保存。

### 保存成功但客户端仍然无法请求怎么办？

请依次确认：

1. 中转站协议与客户端匹配：Codex 使用 Responses API，Claude 使用 Anthropic Messages API。
2. 模型 ID 是中转站实际支持的 ID。
3. 已完全退出并重新打开客户端或终端。
4. Claude Desktop 已选择第三方推理模式。
5. Windows 是否存在覆盖用户策略的机器级 Claude 策略。
6. 服务商是否只接受自定义认证头、SSO 或动态凭据。当前工具只支持 `x-api-key` 和 `bearer`。

### 为什么不能直接填写官网地址？

官网首页通常不是 API 基础地址，也不一定实现客户端需要的协议。请使用服务商明确提供的 API Base URL。

### 为什么原配置没有被覆盖？

如果 Codex TOML 语法无法解析，程序会停止写入，以避免破坏已有配置。请先修复 TOML，或根据程序生成的备份恢复后再重试。

### 如何恢复 Claude Desktop 旧策略？

完全退出 Claude 后，将备份的 `.reg` 文件导入 Windows 注册表，再重新启动 Claude。导入前请检查文件内容，并确认备份来源可信。

## 官方文档

- [Claude Desktop Gateway](https://claude.com/docs/third-party/claude-desktop/gateway.md)
- [Claude Desktop configuration format](https://claude.com/docs/third-party/claude-desktop/configuration-format.md)
- [Claude Desktop configuration sources](https://claude.com/docs/third-party/claude-desktop/configuration.md)
- [Claude Desktop MDM](https://claude.com/docs/third-party/claude-desktop/mdm.md)
- [Python Tkinter](https://docs.python.org/3/library/tkinter.html)
- [PyInstaller](https://pyinstaller.org/)

## 项目状态

当前版本适合在 Windows x64 上进行本地配置和测试。项目没有声称兼容所有中转站；兼容性取决于中转站是否完整实现目标客户端要求的 API、流式输出、工具调用和认证方式。

真实 API 会话验证需要用户使用自己的中转站和 Key 在目标客户端中完成。离线测试结果不等同于对第三方服务的在线可用性保证。

## 许可证

本仓库当前未在文档中声明开源许可证。公开发布前，请在仓库根目录补充 `LICENSE` 文件，并明确允许的使用、修改和再分发范围。
