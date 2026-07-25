---
tags: [工具, Claude]
---

# Claude Code 个人配置完整手册


## 相关笔记

- Skill 构建：[[Claude-Code-Skill构建指南|Skill 构建指南]]
- Agent 对比：[[AI-Coding-Agents-对比|AI Coding Agents 对比]]
- Claude-Code-Skill概念与结构详解：[[Claude-Code-Skill概念与结构详解]]


---
> 最后更新：2026-05-28（补全 Skills 列表：20→44，含 .agents + Superpowers 工作流；修正 Agents 58→48、Commands 76→79）
> 适用环境：Windows 11 + Claude Code CLI v2.1.126

---

## 一、系统环境

| 项目 | 详情 |
|------|------|
| 操作系统 | Windows 11 Pro 10.0.22631 |
| Shell | bash（通过 Git for Windows / MSYS2） |
| Node.js | v24.15.0 |
| npm | 11.12.1 |
| Python | python3 可用 |
| Claude Code 版本 | 2.1.126 |
| 安装方式 | WinGet（包管理器） |
| 安装路径 | `AppData\Local\Microsoft\WinGet\Packages\Anthropic.ClaudeCode_...` |

### Claude Code 的启动方式

- **桌面快捷方式**：`C:\Users\Administrator\Desktop\Claude Code.lnk`
  - 目标：`wt.exe`（Windows 终端）
  - 起始位置：`C:\Users\Administrator`
  - 参数：`--title "Claude Code" claude`
- **开机自启**：`Start Menu\Programs\Startup\claude-code.bat`
  - 开机后等 5 秒，自动启动 Windows Terminal 运行 `claude`
- **手动启动**：任意终端输入 `claude`

### 模型路由

当前通过 DeepSeek API 代理访问，配置在 `~/.claude/settings.json` 的 `env` 字段：

```
ANTHROPIC_BASE_URL = https://api.deepseek.com/anthropic
ANTHROPIC_MODEL = deepseek-v4-pro[1m]
ANTHROPIC_DEFAULT_HAIKU_MODEL = deepseek-v4-flash
ANTHROPIC_DEFAULT_SONNET_MODEL = deepseek-v4-pro[1m]
ANTHROPIC_DEFAULT_OPUS_MODEL = deepseek-v4-pro[1m]
ANTHROPIC_REASONING_MODEL = claude-opus-4-7
```

> **注意**：DeepSeek 代理的 coding 质量不如原生 Claude。如果换回 Anthropic 直连，需修改 `ANTHROPIC_BASE_URL` 和 `ANTHROPIC_AUTH_TOKEN`。

---

## 二、配置文件清单

所有 Claude Code 配置都放在 `C:\Users\Administrator\.claude\` 目录下。

### 2.1 文件关系

```
~/
├── CLAUDE.md                          # 用户级行为指令（始终加载）
└── .claude/
    ├── settings.json                  # 全局配置（用户级）
    ├── settings.local.json            # 本地覆盖（权限 + hooks）
    ├── hooks/
    │   └── hooks.json                 # ECC 插件 hooks（自动加载）
    ├── agents/                        # ECC 安装的 40+ 个 agent
    ├── skills/                        # ECC 安装的 20+ 个 skill
    ├── commands/                      # ECC 安装的 60+ 个命令
    ├── rules/                         # ECC 安装的 14 语言规则
    ├── scripts/                       # ECC 脚本
    ├── projects/                      # claude-mem 项目观察数据
    │   └── C--Users-Administrator/
    │       └── memory/
    │           └── MEMORY.md          # 跨会话记忆索引
    └── ecc/
        └── install-state.json         # ECC 安装状态
```

---

## 三、CLAUDE.md —— 用户级行为指令

**文件位置**：`C:\Users\Administrator\CLAUDE.md`

**作用**：每次 Claude Code 启动时自动加载，定义了 Agent 必须遵守的行为准则。

**内容摘要**（5 条核心规则）：

1. **技术断言必须查证**：不得凭记忆作答，必须查 `man`/`--help`/官方文档或交叉比对两个独立来源
2. **方案设计必须严格区分配置边界**：区分节点部署边界、环境规模边界、推荐标准边界
3. **输出后逆推复验**：写完内容后回头看——数数量、查逻辑链、验可执行性、找遗漏
4. **写笔记/文档时逐条核实**：每条技术断言都核实再落笔
5. **输出标准**：全面无遗漏、逻辑严谨闭环、落地可直接复用、主动预判风险、结构清晰分层、专业标准输出

完整原文见：`C:\Users\Administrator\CLAUDE.md`

---

## 四、settings.json —— 全局配置

**文件位置**：`C:\Users\Administrator\.claude\settings.json`

### 4.1 模型路由（env）

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "ANTHROPIC_REASONING_MODEL": "claude-opus-4-7",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
    "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro[1m]"
  }
}
```

> **换电脑时**：替换 `ANTHROPIC_AUTH_TOKEN` 为你自己的 API key。如果不用 DeepSeek 代理，改成 Anthropic 直连的 URL。

### 4.2 权限模式（permissions）

```json
{
  "permissions": {
    "allow": ["mcp__pencil"],
    "defaultMode": "auto"
  }
}
```

- `defaultMode: "auto"`：安全操作自动放行，危险操作仍需确认
- `allow` 白名单：pencil MCP 工具自动放行

**可选的其他模式**：
- `"default"`：每步都要确认（默认值）
- `"acceptEdits"`：只自动接受文件编辑
- `"dontAsk"`：首次确认后记住
- `"plan"`：只读模式，禁止执行

### 4.3 Fast Mode（已关闭）

```json
{ "fastMode": false }
```

关闭后输出速度稍慢但出错率更低。

### 4.4 已安装的插件

```json
{
  "enabledPlugins": {
    "ui-ux-pro-max@ui-ux-pro-max-skill": true,
    "superpowers@superpowers-marketplace": true,
    "claude-mem@thedotmack": true,
    "andrej-karpathy-skills@karpathy-skills": true
  }
}
```

| 插件 | 来源 | 用途 |
|------|------|------|
| `superpowers@superpowers-marketplace` | github/obra/superpowers-marketplace | 规划、调试、TDD 等结构化工作流 |
| `claude-mem@thedotmack` | github/thedotmack/claude-mem | 跨会话记忆系统 |
| `ui-ux-pro-max@ui-ux-pro-max-skill` | github/nextlevelbuilder/ui-ux-pro-max-skill | UI/UX 设计智能 |
| `andrej-karpathy-skills@karpathy-skills` | github/forrestchang/andrej-karpathy-skills | Karpathy 编码规范 |

### 4.5 插件市场注册

```json
{
  "extraKnownMarketplaces": {
    "thedotmack": { "source": { "source": "github", "repo": "thedotmack/claude-mem" } },
    "ui-ux-pro-max-skill": { "source": { "source": "github", "repo": "nextlevelbuilder/ui-ux-pro-max-skill" } },
    "superpowers-marketplace": { "source": { "source": "github", "repo": "obra/superpowers-marketplace" } },
    "karpathy-skills": { "source": { "source": "github", "repo": "forrestchang/andrej-karpathy-skills" } }
  }
}
```

### 4.6 完整文件

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "ANTHROPIC_REASONING_MODEL": "claude-opus-4-7",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
    "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro[1m]"
  },
  "includeCoAuthoredBy": false,
  "fastMode": false,
  "permissions": {
    "allow": ["mcp__pencil"],
    "defaultMode": "auto"
  },
  "enabledPlugins": {
    "ui-ux-pro-max@ui-ux-pro-max-skill": true,
    "superpowers@superpowers-marketplace": true,
    "claude-mem@thedotmack": true,
    "andrej-karpathy-skills@karpathy-skills": true
  },
  "extraKnownMarketplaces": {
    "thedotmack": {
      "source": { "source": "github", "repo": "thedotmack/claude-mem" }
    },
    "ui-ux-pro-max-skill": {
      "source": { "source": "github", "repo": "nextlevelbuilder/ui-ux-pro-max-skill" }
    },
    "superpowers-marketplace": {
      "source": { "source": "github", "repo": "obra/superpowers-marketplace" }
    },
    "karpathy-skills": {
      "source": { "source": "github", "repo": "forrestchang/andrej-karpathy-skills" }
    }
  }
}
```

---

## 五、settings.local.json —— 本地覆盖

**文件位置**：`C:\Users\Administrator\.claude\settings.local.json`

> **说明**：此文件是 `settings.json` 的本地覆盖，优先级高于 `settings.json`。主要用于权限白名单和 hooks，不会进入版本控制。

### 5.1 权限白名单（113 条规则）

核心覆盖范围：

| 类别 | 示例 | 用途 |
|------|------|------|
| npm/node | `Bash(npm *)`, `Bash(npx *)`, `Bash(node *)` | 前端开发 |
| Python | `Bash(python *)`, `Bash(python3 *)`, `Bash(pip install *)` | 后端/脚本 |
| Git | `Bash(git add *)`, `Bash(git commit *)`, `Bash(git checkout *)` | 版本控制 |
| Claude Code CLI | `Bash(claude *)` | Claude Code 自身操作 |
| curl | `Bash(curl *)` | 网络请求 |
| WebFetch | `WebFetch(domain:github.com)`, `WebFetch(domain:ecc.tools)` | 网页抓取 |
| PowerShell | `Bash(powershell *)` | Windows 系统操作 |
| taskkill | `Bash(taskkill *)` | 进程管理 |
| GitHub | `Bash(gh repo *)` | GitHub CLI |
| 文件系统 | `Read(//c/Program Files/**)` | 读取程序目录 |
| 构建工具 | `Bash(npx tsc *)`, `Bash(npx vitest *)`, `Bash(npx next *)` | TypeScript/测试/Next.js |

完整 113 条见文件原文。

### 5.2 Hooks —— Claude Studio 事件中继

8 个 hook 事件全部中继到 Claude Studio 脚本：

| Hook 事件 | 触发时机 | 目标脚本 |
|----------|---------|---------|
| SessionStart | 会话启动 | `~Desktop/claude-studio/scripts/hooks-relay.sh` |
| SessionEnd | 会话结束 | 同上 |
| PreToolUse | 工具调用前 | 同上 |
| PostToolUse | 工具调用后 | 同上 |
| UserPromptSubmit | 用户提交 prompt | 同上 |
| Stop | 响应完成 | 同上 |
| SubagentStop | 子 agent 停止 | 同上 |
| Notification | 通知事件 | 同上 |

**Hook 格式**（新格式，2026-05-28 修过）：

```json
{
  "matcher": "",
  "hooks": [{
    "type": "command",
    "command": "bash C:/Users/Administrator/Desktop/claude-studio/scripts/hooks-relay.sh"
  }]
}
```

**关键踩坑记录**：
- 旧格式用 `{command, args}` → 新格式用 `{matcher, hooks: [{type, command}]}` —— `/doctor` 报错后修复
- 路径使用**正斜杠** `C:/Users/...` 而非反斜杠 `C:\Users\...` —— 反斜杠会被 JSON + bash 两层转义吃掉

### 5.3 插件覆盖

```json
{ "enabledPlugins": { "claude-mem@thedotmack": false } }
```

`settings.local.json` 中关闭了 claude-mem 插件，`settings.json` 中开启。由于 local 优先级更高，实际上：
- `claude-mem@thedotmack` → **当前关闭**
- 其他 3 个插件 → **开启**

---

## 六、ECC（Everything Claude Code）安装

### 6.1 安装方式

通过 npx 安装（GitHub 直连被网络拦截，API 可用）：

```bash
npx -p ecc-universal ecc-install --profile core --target claude
```

- npm 包名：`ecc-universal`（v1.10.0，next 版本 2.0.0-rc.1）
- CLI 命令：`ecc-install`（包内二进制）
- Profile：`core`（核心组件）
- 安装日期：2026-05-28

### 6.2 安装内容总览

| 组件 | 数量 | 位置 |
|------|------|------|
| Agents（智能体） | 48 | `~/.claude/agents/` |
| Skills（技能） | 44 | `~/.claude/skills/` + `~/.claude/.agents/skills/` |
| Commands（命令） | 79 | `~/.claude/commands/` |
| Rules（规则） | 16 语言 + 中文 | `~/.claude/rules/` |
| Hooks（ECC 钩子） | 30+ | `~/.claude/hooks/hooks.json` |
| Scripts（脚本） | 全套 | `~/.claude/scripts/` |

> **Skills 分两处存放**：ECC 安装的 20 个在 `~/.claude/skills/`，`.agents` 市场安装的 34 个在 `~/.claude/.agents/skills/`。两处有少量重叠（同名 skill 两边都有），去重后共 44 个。

---

### 6.3 Agents（48 个）完整列表

#### 规划与设计（5 个）

| Agent | 用途 |
|-------|------|
| `planner` | 复杂功能和重构的规划，出分步实现方案 |
| `architect` | 系统架构设计、可扩展性、技术决策 |
| `code-architect` | 分析现有代码库模式，生成实现蓝图 |
| `gan-planner` | 将一句话需求展开为完整产品规格 |
| `chief-of-staff` | 邮件/Slack/LINE 等多渠道沟通分类和回复草稿 |

#### 代码审查（12 个语言/平台）

| Agent | 审查对象 |
|-------|---------|
| `code-reviewer` | **通用**代码质量、安全、可维护性 |
| `typescript-reviewer` | TypeScript/JavaScript |
| `python-reviewer` | Python（PEP 8、类型注解、安全） |
| `go-reviewer` | Go（惯用写法、并发安全、错误处理） |
| `java-reviewer` | Java/Spring Boot |
| `kotlin-reviewer` | Kotlin/Android/KMP |
| `rust-reviewer` | Rust（所有权、生命周期、unsafe） |
| `cpp-reviewer` | C++（内存安全、现代 C++、并发） |
| `csharp-reviewer` | C#（.NET 规范、async、安全） |
| `flutter-reviewer` | Flutter/Dart |
| `database-reviewer` | PostgreSQL 查询优化、Schema 设计、Supabase |
| `security-reviewer` | **安全**漏洞检测、OWASP Top 10 |

#### 构建修复（9 个语言/平台）

| Agent | 修复对象 |
|-------|---------|
| `build-error-resolver` | **通用**构建 + TypeScript 类型错误 |
| `go-build-resolver` | Go 构建错误 |
| `java-build-resolver` | Java/Maven/Gradle |
| `kotlin-build-resolver` | Kotlin/Gradle |
| `rust-build-resolver` | Rust/Cargo |
| `cpp-build-resolver` | C++/CMake/链接错误 |
| `dart-build-resolver` | Dart/Flutter |
| `pytorch-build-resolver` | PyTorch/CUDA 训练错误 |
| `gan-build` | GAN Harness 构建 |

#### 测试（3 个）

| Agent | 用途 |
|-------|------|
| `tdd-guide` | 强制执行"先写测试"方法论，80%+ 覆盖率 |
| `e2e-runner` | 端到端测试（Playwright + Vercel Agent Browser） |
| `pr-test-analyzer` | 审查 PR 测试覆盖质量和完整性 |

#### 代码质量与清理（8 个）

| Agent | 用途 |
|-------|------|
| `code-simplifier` | 简化和精炼代码，保持行为不变 |
| `refactor-cleaner` | 死代码检测和清理（knip/depcheck/ts-prune） |
| `comment-analyzer` | 分析代码注释的准确性和维护性 |
| `type-design-analyzer` | 分析类型设计的封装和约束表达 |
| `silent-failure-hunter` | 审查静默失败、被吞掉的错误、错误传播 |
| `performance-optimizer` | 性能瓶颈分析、打包体积优化 |
| `a11y-architect` | WCAG 2.2 无障碍合规 |
| `seo-specialist` | 技术 SEO 审计、结构化数据、Core Web Vitals |

#### 工作流与编排（6 个）

| Agent | 用途 |
|-------|------|
| `loop-operator` | 自主循环执行、监控、安全介入 |
| `harness-optimizer` | 分析和优化 agent harness 配置 |
| `gan-generator` | GAN Harness 代码生成器 |
| `gan-evaluator` | GAN Harness 评估器 |
| `gan-planner` | GAN Harness 规划器 |
| `code-explorer` | 深度分析代码库，追踪执行路径 |

#### 文档与学习（3 个）

| Agent | 用途 |
|-------|------|
| `doc-updater` | 文档和 codemap 同步更新 |
| `docs-lookup` | 查询最新库/框架/API 文档（Context7 MCP） |
| `conversation-analyzer` | 分析对话记录，提取可 hook 的行为模式 |

#### 开源与合规（4 个）

| Agent | 用途 |
|-------|------|
| `opensource-forker` | 创建开源 fork，脱敏密钥/PII |
| `opensource-sanitizer` | 开源发布前的安全审计（20+ regex 扫描） |
| `opensource-packager` | 生成 CLAUDE.md/README/LICENSE/模板 |
| `healthcare-reviewer` | 医疗应用代码审查（临床安全、PHI 合规） |

---

### 6.4 Skills（44 个）完整列表

Skills 分两处存放：ECC 安装的 20 个（`~/.claude/skills/`）和 `.agents` 市场安装的 34 个（`~/.claude/.agents/skills/`）。去重后共 44 个。

#### 6.4.1 开发流程（7 个）

| Skill | 来源 | 用途 |
|-------|------|------|
| `tdd-workflow` | ECC + .agents | 测试驱动开发流程，80%+ 覆盖率 |
| `code-tour` | ECC | 创建 CodeTour `.tour` 文件——分步骤代码走读 |
| `iterative-retrieval` | ECC | 渐进式上下文检索，解决 subagent 上下文问题 |
| `strategic-compact` | ECC + .agents | 在逻辑断点建议手动压缩上下文 |
| `agent-introspection-debugging` | ECC + .agents | AI agent 失败的结构化自调试流程 |
| `dmux-workflows` | .agents | 多路复用工作流编排 |
| `everything-claude-code` | .agents | ECC 全套安装/配置管理 |

#### 6.4.2 测试与质量（6 个）

| Skill | 来源 | 用途 |
|-------|------|------|
| `e2e-testing` | ECC + .agents | Playwright E2E 测试模式、Page Object Model |
| `eval-harness` | ECC + .agents | 评估驱动开发（EDD）框架 |
| `verification-loop` | ECC + .agents | 综合验证系统 |
| `ai-regression-testing` | ECC | AI 辅助开发的回归测试策略 |
| `plankton-code-quality` | ECC | 写时代码质量强制（格式化/linting/修复） |
| `skill-stocktake` | ECC | 审计 skills 和 commands 质量 |

#### 6.4.3 安全与审查（2 个）

| Skill | 来源 | 用途 |
|-------|------|------|
| `security-review` | .agents | 全面安全审查（OWASP、密钥检测、CVE 扫描） |
| `coding-standards` | .agents | 编码标准检查（语言无关） |

#### 6.4.4 前端与设计（6 个）

| Skill | 来源 | 用途 |
|-------|------|------|
| `frontend-design` | ECC + .agents | 生产级前端界面设计，避免泛化 AI 风格 |
| `vercel-react-best-practices` | ECC（symlink） | Vercel React/Next.js 性能优化指南 |
| `frontend-patterns` | .agents | 前端架构模式（状态管理、数据获取、路由） |
| `frontend-slides` | .agents | 前端技术演示幻灯片生成 |
| `nextjs-turbopack` | .agents | Next.js + Turbopack 最佳实践 |
| `fal-ai-media` | .agents | Fal AI 媒体生成（图片/视频） |

#### 6.4.5 后端与 API（4 个）

| Skill | 来源 | 用途 |
|-------|------|------|
| `api-design` | .agents | REST/GraphQL/gRPC API 设计规范 |
| `backend-patterns` | .agents | 后端架构模式（CQRS、Event Sourcing、微服务） |
| `mcp-server-patterns` | .agents | MCP Server 开发模式和最佳实践 |
| `bun-runtime` | .agents | Bun 运行时专项（打包、测试、部署） |

#### 6.4.6 AI / LLM 开发（2 个）

| Skill | 来源 | 用途 |
|-------|------|------|
| `claude-api` | .agents | Claude API / Anthropic SDK 开发（含 prompt caching） |
| `deep-research` | .agents | 多轮深度研究，适合复杂技术调研 |

#### 6.4.7 内容与写作（6 个）

| Skill | 来源 | 用途 |
|-------|------|------|
| `article-writing` | .agents | 技术文章/博客写作 |
| `brand-voice` | .agents | 品牌语调一致性管理 |
| `content-engine` | .agents | 内容引擎——批量内容生成流水线 |
| `crosspost` | .agents | 跨平台内容发布（Dev.to、Medium、Hashnode） |
| `documentation-lookup` | .agents | 库/框架/API 文档查询（Context7 MCP） |
| `exa-search` | .agents | Exa 语义搜索引擎集成 |

#### 6.4.8 产品与商业（4 个）

| Skill | 来源 | 用途 |
|-------|------|------|
| `product-capability` | .agents | 产品能力分析和需求定义 |
| `market-research` | .agents | 市场调研、竞品分析 |
| `investor-materials` | .agents | 投资人材料（Pitch Deck、Teaser、Data Room） |
| `investor-outreach` | .agents | 投资人外联策略和邮件模板 |

#### 6.4.9 持续学习（2 个）

| Skill | 来源 | 用途 |
|-------|------|------|
| `continuous-learning-v2` | ECC | 本能驱动持续学习（observer→instinct→skill 演进） |
| `continuous-learning` | ECC | 旧版 v1 Stop-hook 模式提取 |

#### 6.4.10 配置与管理（5 个）

| Skill | 来源 | 用途 |
|-------|------|------|
| `configure-ecc` | ECC | ECC 交互式安装向导 |
| `find-skills` | ECC（symlink） | 查找和安装新 skill |
| `agent-sort` | ECC + .agents | 为特定仓库构建精简的 ECC 安装方案 |
| `hookify-rules` | ECC | 创建和管理 hookify 规则 |
| `council` | ECC | 四人审议委员会——应对模糊决策、权衡、go/no-go |

#### 6.4.11 其他工具（3 个）

| Skill | 来源 | 用途 |
|-------|------|------|
| `video-editing` | .agents | 视频编辑脚本生成和处理 |
| `x-api` | .agents | X/Twitter API 集成 |
| `api-design` | .agents | API 设计审查（同 6.4.5，双重分类） |

> **说明**：部分 skill 同时出现在 ECC 和 `.agents` 两处（标记为"ECC + .agents"），内容可能略有差异，实际调用时以优先级高的为准。

#### 6.4.12 Superpowers 工作流 Skills（14 个）

以下 skills 来自 `superpowers@superpowers-marketplace` 插件，在会话中可直接通过 `/skill-name` 调用，不存放在文件系统中：

| Skill | 用途 |
|-------|------|
| `brainstorming` | 创意工作前必用——探索用户意图、需求和设计方向 |
| `writing-plans` | 有 spec/需求时的多步骤实现方案编写 |
| `executing-plans` | 在独立会话中按审查检查点执行实现计划 |
| `subagent-driven-development` | 当前会话中按独立任务并行执行实现计划 |
| `systematic-debugging` | 遇到 bug/测试失败/异常行为时（在提出修复之前）使用 |
| `verification-before-completion` | 声明工作"完成/修复/通过"前，必须先跑验证命令 |
| `requesting-code-review` | 完成任务、实现功能后或合并前验证工作 |
| `receiving-code-review` | 收到 code review 反馈时，先做技术验证再实施 |
| `test-driven-development` | 实现任何功能或 bugfix 前，先写测试 |
| `finishing-a-development-branch` | 实现完成、测试通过后，决定如何合并/PR/清理 |
| `using-git-worktrees` | 创建隔离的 git worktree 用于独立开发 |
| `using-superpowers` | 每次对话启动时建立 skill 查找规范 |
| `dispatching-parallel-agents` | 2+ 个无共享状态的独立任务并行调度 |
| `writing-skills` | 创建/编辑/验证新 skill 文件 |

> **Superpowers 与 ECC 的关系**：Superpowers 定义"怎么做事"的工作流规范；ECC/`.agents` 提供"做事时用什么工具"的 agents/commands/skills。

---

### 6.5 Commands（79 个）详细列表

#### 核心开发命令

| 命令 | 用途 | 调用 Agent |
|------|------|-----------|
| `/plan "需求"` | 出实现方案，等确认再动手 | planner |
| `/code-review [PR#]` | 代码审查（本地或 GitHub PR） | code-reviewer |
| `/build-fix` | 修复构建/类型错误 | build-error-resolver |
| `/refactor-clean` | 清理死代码和重复 | refactor-cleaner |
| `/quality-gate` | 质量门验证检查 | — |
| `/feature-dev` | 有指导的功能开发，含代码库理解 | — |
| `/security-scan` | 安全漏洞扫描（via AgentShield） | security-reviewer |

#### 语言专项审查命令

| 命令 | 审查/操作对象 |
|------|-------------|
| `/go-review` | Go 代码审查 |
| `/go-build` | Go 构建错误修复 |
| `/go-test` | Go TDD 工作流 |
| `/python-review` | Python 代码审查 |
| `/cpp-review` | C++ 代码审查 |
| `/cpp-build` | C++ 构建错误修复 |
| `/cpp-test` | C++ TDD 工作流 |
| `/rust-review` | Rust 代码审查 |
| `/rust-build` | Rust 构建修复 |
| `/rust-test` | Rust TDD 工作流 |
| `/kotlin-review` | Kotlin 审查 |
| `/kotlin-build` | Kotlin/Gradle 构建修复 |
| `/kotlin-test` | Kotlin TDD 工作流 |
| `/flutter-review` | Flutter/Dart 审查 |
| `/flutter-build` | Flutter 构建修复 |
| `/flutter-test` | Flutter 测试 |
| `/gradle-build` | Gradle 构建修复（Android/KMP） |

#### 持续学习命令

| 命令 | 用途 |
|------|------|
| `/learn` | 从会话提取可复用模式 |
| `/learn-eval` | 提取 + 自评 + 保存 |
| `/instinct-status` | 查看已学到的 instinct（含置信度） |
| `/instinct-import <file>` | 从文件/URL 导入 instinct |
| `/instinct-export` | 导出 instinct |
| `/evolve` | 聚类 instinct → skill/command/agent |
| `/prune` | 删除 30 天+未提升的待处理 instinct |
| `/promote [id]` | 将项目级 instinct 提升为全局 |
| `/projects` | 列出已知项目和 instinct 统计 |

#### 会话管理

| 命令 | 用途 |
|------|------|
| `/sessions` | 管理会话历史和别名 |
| `/save-session` | 保存当前会话状态到文件 |
| `/resume-session` | 从最近会话恢复 |
| `/checkpoint` | 保存验证状态 |

#### 项目管理

| 命令 | 用途 |
|------|------|
| `/prp-plan` | 创建功能实现计划（含代码库分析） |
| `/prp-implement` | 执行实现计划（含验证循环） |
| `/prp-commit` | 自然语言描述提交内容 |
| `/prp-pr` | 从当前分支创建 GitHub PR |
| `/prp-prd` | 交互式 PRD 生成器 |
| `/review-pr` | 综合 PR 审查（多 agent） |

#### 多 Agent 编排

| 命令 | 用途 |
|------|------|
| `/multi-plan` | 多 agent 协同规划 |
| `/multi-execute` | 多 agent 协同执行 |
| `/multi-backend` | 后端多服务编排 |
| `/multi-frontend` | 前端多服务编排 |
| `/multi-workflow` | 通用多服务工作流 |

#### 钩子管理

| 命令 | 用途 |
|------|------|
| `/hookify` | 从对话分析创建 hooks |
| `/hookify-configure` | 交互式开关 hookify 规则 |
| `/hookify-list` | 列出所有 hookify 规则 |
| `/hookify-help` | hookify 系统帮助 |

#### 其他实用命令

| 命令 | 用途 |
|------|------|
| `/aside` | 快速侧问，不丢失当前任务上下文 |
| `/setup-pm` | 配置首选包管理器（npm/pnpm/yarn/bun） |
| `/skill-create` | 从 git 历史分析生成 SKILL.md |
| `/skill-health` | 显示 skill 健康仪表盘 |
| `/test-coverage` | 测试覆盖率分析 |
| `/update-docs` | 更新文档 |
| `/update-codemaps` | 更新 codemap |
| `/santa-loop` | 对抗双审查收敛循环 |
| `/model-route` | 模型路由 |
| `/harness-audit` | Harness 审计 |
| `/loop-start` / `/loop-status` | 循环任务管理 |
| `/jira <ticket>` | Jira 票据分析和更新 |
| `/pm2` | PM2 服务生命周期管理 |

#### 旧版 shim 命令（建议直接用 skill）

| 命令 | 对应 skill |
|------|-----------|
| `/tdd` → | `tdd-workflow` |
| `/e2e` → | `e2e-testing` |
| `/eval` → | `eval-harness` |
| `/verify` → | `verification-loop` |
| `/orchestrate` → | `dmux-workflows` |
| `/agent-sort` → | `agent-sort` |
| `/docs` → | `documentation-lookup` |
| `/devfleet` → | `claude-devfleet` |
| `/rules-distill` → | `rules-distill` |
| `/prompt-optimize` → | `prompt-optimizer` |
| `/context-budget` → | `context-budget` |
| `/claw` → | `nanoclaw-repl` |

---

### 6.6 Rules（16 个语言/领域）

安装的规则按语言组织，每个目录含 5-10 个 `.md` 文件：

| 规则目录 | 内容 | 适用范围 |
|---------|------|---------|
| `common/` | 编码风格、Git 工作流、测试、安全、性能、模式、hooks、agent 使用 | 所有项目（始终加载） |
| `typescript/` | TS/JS 特定编码风格、hooks、安全、测试、模式 | TypeScript/JavaScript 项目 |
| `python/` | Python 编码风格、hooks、安全、测试、模式 | Python 项目 |
| `golang/` | Go 编码风格、hooks、安全、测试、模式 | Go 项目 |
| `java/` | Java 编码风格、hooks、安全、测试、模式 | Java 项目 |
| `kotlin/` | Kotlin 编码风格、hooks、安全、测试、模式 | Kotlin/Android 项目 |
| `rust/` | Rust 编码风格、hooks、安全、测试、模式 | Rust 项目 |
| `cpp/` | C++ 编码风格、hooks、安全、测试、模式 | C++ 项目 |
| `csharp/` | C# 编码风格、hooks、安全、测试、模式 | C# 项目 |
| `swift/` | Swift 编码风格、hooks、安全、测试、模式 | Swift 项目 |
| `php/` | PHP 编码风格、hooks、安全、测试、模式 | PHP 项目 |
| `perl/` | Perl 编码风格、hooks、安全、测试、模式 | Perl 项目 |
| `dart/` | Dart 编码风格、hooks、安全、测试、模式 | Dart/Flutter 项目 |
| `web/` | Web 特定：CSS/HTML 编码风格、设计质量、性能、安全 | 前端项目 |
| `zh/` | **中文版** common 规则（agents、code-review、coding-style 等 11 个文件） | 中文项目 |

---

### 6.7 ECC Hooks 功能

ECC hooks 与 Claude Studio hooks **互不冲突**，分别独立运行：

| 触发时机 | ECC 自动行为 |
|---------|------------|
| Bash 命令前 | 阻止 `--no-verify`、tmux 提醒、commit 质量检查 |
| 编辑/写入后 | console.log 警告、设计质量检查、格式+类型检查 |
| 写入前 | 阻止篡改 linter 配置、文档文件警告 |
| Session 启动 | 加载上次上下文 |
| Stop/SessionEnd | 格式化检查、会话状态持久化、cost 统计 |
| PreCompact | 压缩前保存状态 |

---

## 七、Claude Studio

**位置**：`C:\Users\Administrator\Desktop\claude-studio\`

- 一个独立的自定义工具，通过 hooks relay 脚本监听 Claude Code 的所有事件
- 桌面有 `Claude Studio.lnk` 快捷方式，指向 `claude-studio.bat`
- **当 hooks-relay.sh 路径错误时**（见第五章踩坑记录），会在终端刷大量 hook error
- **E:\claude-studio 备份**：`C:\Users\Administrator\Desktop\claude-studio\`

---

## 八、桌面快捷方式 & 开机自启

### 8.1 Claude Code 快捷方式

- **文件**：`C:\Users\Administrator\Desktop\Claude Code.lnk`
- **目标**：`wt.exe`（Windows Terminal）
- **起始位置**：`C:\Users\Administrator`
- **参数**：`--title "Claude Code" claude`

> **起始位置是 `C:\Users\Administrator`**，所以双击启动时 Claude Code 的工作目录是 home 目录，不会加载项目级 CLAUDE.md。

### 8.2 开机自启

- **文件**：`C:\Users\Administrator\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\claude-code.bat`
- **内容**：等 5 秒后启动 Windows Terminal 运行 `claude`

---

## 九、跨会话记忆系统（claude-mem）

### 9.1 状态

- claude-mem 插件在 `settings.json` 中开启，但在 `settings.local.json` 中被覆盖为 **关闭**
- 观察数据保存在 `~/.claude/projects/C--Users-Administrator/memory/`
- 当前积累了大量观察记录（50+ 条），覆盖 2026 年 5 月的开发活动

### 9.2 如果要重新启用

在 `settings.local.json` 中删除或改为：
```json
"enabledPlugins": { "claude-mem@thedotmack": true }
```

---

## 十、换电脑迁移清单

### 10.1 必须拷贝的文件

```
源机器 → 新机器，相同路径：

C:\Users\<用户名>\
├── CLAUDE.md
└── .claude\
    ├── settings.json                  # 全局配置（修改 API key）
    ├── settings.local.json            # 权限 + hooks
    ├── agents\                        # ECC agents
    ├── skills\                        # ECC skills
    ├── commands\                      # ECC commands
    ├── rules\                         # ECC rules
    ├── hooks\
    │   └── hooks.json                 # ECC hooks
    ├── scripts\                       # ECC 脚本
    └── ecc\                           # ECC 安装状态
```

### 10.2 安装步骤

```powershell
# 1. 安装 Claude Code CLI
winget install Anthropic.ClaudeCode

# 2. 安装 Node.js（如果需要）
winget install OpenJS.NodeJS

# 3. 拷贝所有配置文件到对应位置

# 4. 修改 settings.json 中的 API key

# 5. 安装 ECC（如果不想拷贝文件，可以重新安装）
npx -p ecc-universal ecc-install --profile core --target claude

# 6. 创建桌面快捷方式
# 目标：wt.exe
# 起始位置：C:\Users\<用户名>
# 参数：--title "Claude Code" claude

# 7. 验证
claude --version
claude
/doctor
```

### 10.3 不需要拷贝的

- `~/.claude/projects/`（claude-mem 观察数据，除非需要跨会话记忆）
- `~/.claude/memory/`（同）
- 桌面 `Claude Studio` 目录（独立工具，按需拷贝）

---

## 十一、遇到的问题及修复记录

| 日期 | 问题 | 修复 |
|------|------|------|
| 2026-05-28 | `/doctor` 报告 8 个 hook 事件 `hooks` 字段为 undefined | 将旧格式 `{command, args}` 改为新格式 `{matcher, hooks: [{type, command}]}` |
| 2026-05-28 | Hook relay 脚本路径报错：`C:UsersAdministratorDesktopclaude-studioscripts...` | 将路径中的反斜杠 `\\` 全部换成正斜杠 `/` |
| 2026-05-28 | 每次操作都要手动确认，效率低 | 设 `defaultMode: "auto"` |
| 2026-05-28 | 发现 fast mode 导致偶尔输出错字 | 设 `fastMode: false` |
| 2026-05-28 | settings.json 尝试顶层 `permissionMode` 被 schema 拒绝 | 改为 `permissions.defaultMode` |
| 2026-05-28 | npx ecc-install 直接报 404 | 改用 `npx -p ecc-universal ecc-install`（包名和二进制名不同） |
| 2026-05-28 | GitHub raw/git 协议被网络拦截 | 通过 GitHub API（`api.github.com`）获取内容 |
| 2026-05-28 | ECC 安装后 hooks 与 Claude Studio hooks 是否会冲突 | 确认：两者在不同文件中定义，event 不同，独立运行 |

---

## 十二、相关笔记文档

桌面上已有的参考文档：

| 文档 | 路径 |
|------|------|
| AI 编程 Agent 协作方法论 | `桌面/笔记/AI编程Agent协作方法论.md` |
| DNS 解析原理 | `桌面/笔记/DNS解析原理.md` |
| 软件包后缀含义 | `桌面/笔记/软件包后缀含义与dnf依赖解析.md` |
| 生产环境软件升级 | `桌面/笔记/生产环境软件升级与打补丁.md` |
| Ops 日志查看工具 | `桌面/笔记/Ops日志查看工具参考.md` |
| 运维学习项目路线图 | `桌面/运维学习项目路线图.md` |
| AI 与运维结合实战指南 | `桌面/AI与运维结合实战指南.md` |
| 运维工程师岗位研究 | `桌面/运维工程师岗位市场研究_2025-2026.md` |
