---
tags: [工具, Agent, 对比]
---

# Claude Code vs Hermes Agent vs Codex CLI — 全面对比


## 相关笔记

- 本文是 Claude Code、Hermes 与 Codex 的唯一维护版本。
- Skill 开发：[[Claude-Code-Skill构建指南|Skill 构建指南]]
- 编排应用：[[Agent/Agent-Skill与多Agent编排深度分析|Skill + 编排分析]]

---
> 整理时间：2026-05-27
> 依据来源：各项目官方文档 + SKILL.md 实测信息

---

## 一、定位与一句话描述

| 工具 | 定位 |
|------|------|
| **Claude Code** | Anthropic 官方 Claude 专用终端编程代理，深度绑定 Claude 模型 |
| **Hermes Agent** | Nous Research 开源通用 AI 代理框架，不绑定任何模型，自学习 + 多平台 |
| **Codex CLI** | OpenAI 官方编程代理 CLI，深度绑定 OpenAI 模型（GPT/Codex） |

---

## 二、模型自由度

| | Claude Code | Hermes Agent | Codex CLI |
|---|---|---|---|
| 绑定模型 | 仅 Anthropic Claude 系列 | **无绑定** | 仅 OpenAI 系列 |
| 可用模型 | Sonnet / Opus / Haiku | 20+ 提供商（DeepSeek、Anthropic、OpenAI、Google、本地模型等） | GPT-4o / o3 / o4-mini 等 |
| 切换模型 | 同系列内切换 | `hermes model` 随时任意切 | 同系列内切换 |
| 本地模型 | 不支持 | 支持（llama.cpp、Ollama 等） | 不支持 |
| API 密钥 | ANTHROPIC_API_KEY 或 OAuth | 按提供商各自配置 | OPENAI_API_KEY 或 OAuth |

---

## 三、运行平台

| | Claude Code | Hermes Agent | Codex CLI |
|---|---|---|---|
| 终端 CLI | ✅ 原生 TUI（交互式 REPL） | ✅ prompt_toolkit 交互式 | ✅ 交互式终端 |
| 消息平台 | ❌ | ✅ 核心功能 — Telegram / Discord / Slack / 微信 / 飞书 等 10+ 平台 | ❌ |
| Web 界面 | claude.ai + remote-control | Open WebUI / API Server 适配 | ❌ |
| IDE 集成 | `--ide` 自动连接 | ACP 服务器 + MCP | ❌ |
| 桌面 GUI | ❌ | ❌ | ❌ |

---

## 四、会话与记忆

| | Claude Code | Hermes Agent | Codex CLI |
|---|---|---|---|
| 会话存储 | 按目录存，`--continue` 恢复最近 | SQLite 全文索引，`session_search` 搜索历史 | 基本会话恢复 |
| 跨会话持久记忆 | ❌（CLAUDE.md 是静态文件，自动记忆仅 25KB） | ✅ `memory` 工具，持久化偏好/环境事实 | ❌ |
| 项目上下文 | CLAUDE.md + `.claude/rules/` | AGENTS.md + 技能系统 | 基础项目上下文 |
| 多 Profile | ❌ | ✅ 独立配置/技能/记忆的隔离实例 | ❌ |
| 会话搜索 | ❌ | ✅ `session_search` FTS5 全文搜索 | ❌ |

---

## 五、技能 / 知识系统

| | Claude Code | Hermes Agent | Codex CLI |
|---|---|---|---|
| 技能创建 | 手动写 `.claude/skills/*.md` | **自动从经验中学习**，保存为可复用技能 | ❌ |
| 技能积累 | 每个项目手动维护 | 跨会话自动积累，越用越强 | ❌ |
| 技能市场 | ❌ | ✅ `hermes skills browse` | ❌ |
| 自定义命令 | `/` slash 命令 + `!` bash 直通 | `/` slash 命令 | 有限的指令模式 |
| 技能修补 | 手动编辑文件 | `skill_manage(action='patch')` 动态修补 | ❌ |

---

## 六、Agent 能力（多代理 / 委派）

| | Claude Code | Hermes Agent | Codex CLI |
|---|---|---|---|
| 子代理 | `@agent-name` 自定义 agent 团队 | `delegate_task` 同步委派 | ❌ |
| 最大并发 | 团队模式（in-process 或 tmux） | 最多 3 并发子代理 | ❌ |
| 工作树隔离 | ✅ `-w` + `--tmux` 一键 | ✅ `-w` git worktree | ❌（需手动 worktree） |
| 定时任务 | `/loop` 会话内循环 | `cronjob` 持久化调度器 | ❌ |
| 后台任务 | ❌ | `terminal(background=True)` | ❌ |
| Kanban 多代理协作 | ❌ | ✅ 持久化 SQLite 任务队列 | ❌ |

---

## 七、工具生态

| | Claude Code | Hermes Agent | Codex CLI |
|---|---|---|---|
| 核心工具 | Read / Write / Edit / Bash / WebSearch / WebFetch | terminal / file / web / browser / vision / image_gen / 等 30+ | 文件操作 / 终端 / 基础搜索 |
| 工具扩展 | MCP 服务器 | MCP 服务器 + Python 插件 | ❌ |
| Hook 系统 | ✅ 8 种事件 hook（PreToolUse / PostToolUse 等） | ❌（通过技能和插件替代） | ❌ |
| 浏览器自动化 | Puppeteer MCP | Browserbase / Camofox / Chromium | ❌ |
| 代码执行沙箱 | ❌ | ✅ `execute_code` Python 沙箱 | ❌ |
| 图片/视频/语音 | ❌ | ✅ vision / image_gen / video / TTS / STT | ❌ |
| 智能家居 / Spotify | ❌ | ✅ | ❌ |

---

## 八、安全与权限

| | Claude Code | Hermes Agent | Codex CLI |
|---|---|---|---|
| 权限模式 | Normal / Auto-Accept / Plan / Bypass | manual / smart / off | `--full-auto` / `--yolo` |
| 命令审批 | 交互式对话框 | 终端内确认 + `--yolo` 跳过 | sandbox 内自动批准 |
| 工具白名单 | `--allowedTools` 精细控制 | `hermes tools enable/disable` | ❌ |
| 密钥脱敏 | ❌ | ✅ `security.redact_secrets` | ❌ |
| PII 脱敏 | ❌ | ✅ `privacy.redact_pii` | ❌ |
| 凭证池轮换 | ❌ | ✅ 多 API key 自动轮换 | ❌ |
| 文件系统检查点 | ❌ | ✅ `/rollback` 回滚 | ❌ |

---

## 九、输出能力

| | Claude Code | Hermes Agent | Codex CLI |
|---|---|---|---|
| 结构化 JSON | ✅ `--output-format json` + `--json-schema` | ❌ | ❌ |
| 流式输出 | ✅ `stream-json` + 双向流 | ✅ 终端实时流式 | ✅ 终端流式 |
| 非交互模式 | ✅ `claude -p "query"` | ✅ `hermes chat -q "query"` | ✅ `codex exec "prompt"` |
| 管道输入 | ✅ | ✅ | ❌ |

---

## 十、开源与定价

| | Claude Code | Hermes Agent | Codex CLI |
|---|---|---|---|
| 许可证 | 闭源 | **MIT 开源** | 闭源 |
| 安装方式 | `npm install -g @anthropic-ai/claude-code` | `curl ... \| bash` 或 pip | `npm install -g @openai/codex` |
| 使用成本 | Anthropic API 按量付费 或 Pro/Max 订阅 | **取决于所选模型**（可用免费/廉价模型） | OpenAI API 按量付费 |
| 免费额度 | Pro 订阅有使用上限 | DeepSeek / Gemini 等有免费层 | 有限的免费 tier |
| 代码可见 | ❌ | ✅ 完全可审计 | ❌ |

---

## 十一、Windows 支持

| | Claude Code | Hermes Agent | Codex CLI |
|---|---|---|---|
| 原生 Windows | ✅ | ✅ | ✅ |
| WSL | ✅ | ✅ | ✅ |
| Windows 特殊处理 | 基本可用 | 专门 Windows 适配（Ctrl+Enter 换行等） | 基本可用 |

---

## 十二、总结：怎么选？

### 选 Claude Code，如果：
- 你已经是 Anthropic 生态用户
- 需要结构化 JSON 输出做自动化流水线
- 需要精细的 hook 系统和权限控制
- 需要 agent 团队并行协作（@agent-name）
- 不在意模型锁定和闭源

### 选 Hermes Agent，如果：
- 需要模型自由（今天用 DeepSeek 省钱，明天用 Claude 攻坚）
- 需要跨会话持久记忆，让 Agent 越来越了解你的偏好
- 需要在手机（Telegram/Discord/微信）上随时使用
- 需要开源可审计、可扩展
- 需要定时任务、多 Profile 隔离、Kanban 多代理协作
- 需要完整的工具生态（浏览器、图片、语音、智能家居等）

### 选 Codex CLI，如果：
- 你已经是 OpenAI 生态用户
- 任务简单直接，不需要复杂代理能力
- 偏好轻量级工具，功能需求不复杂
- 主要用于 git 仓库内的编程任务

### 三者关系
三者**不是互斥的**。Hermes Agent 可以**作为上层编排器**，通过 `delegate_task` 或 `terminal` 调用 Claude Code 和 Codex CLI 作为子代理。一个常见模式是：用 Hermes 做总控（记忆 + 调度 + 多平台），根据任务类型分发给 Claude Code 或 Codex 执行具体编程任务。
