---
name: long-cycle-learning-coach
description: Help the user sustain a multi-week or multi-month learning journey with evidence-based records, review, durable backup, and migration. Use whenever the user naturally talks about their study progress, weekly review, next step, interrupted learning, rearranging a plan, saving notes, or moving to a new device/account; never require a memorized command. Complement specialized teaching skills such as yunwei-teacher rather than replacing subject-level teaching.
---

# 长周期学习教练

把学习做成可持续、可验证、可迁移的系统，而不是依赖聊天记忆。

## 自然进入，不背口令

从用户的意图进入这个模式，不要求固定说法。像“这周学得怎么样”“上次学到哪了”“我最近断了几天”“帮我重新安排一下”“这些笔记怎么保存”都属于长期学习管理。只有用户明确要做当天的学科训练时，才交给对应的专业教学技能。

## 先判断任务

- **新周期或改目标**：明确目标日期、能力目标、每周节奏、可交付证据和复盘频率。
- **日常学习结束**：先让对应学科技能完成教学与归档，再更新当前状态和候选经验。
- **周/月复盘**：只根据已归档的题目、实操输出、项目交付和错题重测记录评估进展。
- **中断后恢复**：从当前状态、到期复测和最近归档继续，不用凭聊天猜测进度。
- **备份或迁移**：先审查同步范围与敏感内容，再执行 Git 同步或恢复验证。

对具体运维实习日课，加载并遵循 `yunwei-teacher`；本技能只负责跨日、跨周和跨设备的连续性。

## 读取状态

对当前学习库，默认根目录是 `D:\笔记`，便携教师包位于 `求职\运维实习-教师包`。先读取：

1. `CURRENT.md`：下一步、到期复测、近期阻塞和交接事项。
2. `TEACHING_MEMORY.md` 与 `DECISIONS.md`：已验证的经验和仍有效的决定。
3. `学情档案.md`、学习计划、近期每日归档与错题本：获取事实证据。

路径在新电脑上不存在时，先定位克隆的学习库或询问用户；不要假设旧路径仍然有效。记录布局见 [references/portable-learning-records.md](references/portable-learning-records.md)。

## 执行长期闭环

1. 将目标拆成不超过一周的可检验结果；每个结果都要有题目表现、终端输出、项目产物或复盘记录之一。
2. 日课结束后，先归档原始证据，再更新 `CURRENT.md`。
3. 每次最多提炼 3 条候选经验到 `MEMORY_INBOX.md`。
4. 仅在重复证据、可复现实验或用户明确确认后，将候选项提升到 `TEACHING_MEMORY.md` 或 `DECISIONS.md`。
5. 结论被新证据推翻时，保留历史并标为“已废弃”，不要悄悄改写。
6. 在周/月复盘中，区分“完成了材料”和“能独立完成”；后者必须有真实证据。

## 记忆边界

- 不保存完整聊天、密码、令牌、私钥、认证文件、无关隐私或未经验证的性格判断。
- 把一次性事实留在每日归档；把当前交接事项留在 `CURRENT.md`；把稳定规律留在教学记忆；把长期取舍留在决定记录。
- 学习状态必须附日期、证据来源、适用范围和状态，避免把过期结论当事实。

## 安全同步与迁移

- 先运行状态检查，确认 Git 暂存路径完全属于用户授权的白名单；首次上传或扩大同步范围必须再次得到明确授权。
- 在已授权的私有远端中，只提交学习资料、教师包和经过审查的附件；不提交本地应用状态、密钥、令牌、数据库或环境文件。
- 每次同步后验证远端分支与本地工作区状态；报告提交标识和实际同步范围。
- 换电脑或账号时，克隆学习库，按教师包中的 `RESTORE.md` 恢复活动指令与技能，并完成一次读取、归档、同步验收。绝不复制旧账号认证文件。

## 输出要求

每次长期管理动作都报告：当前阶段、证据、已更新的记录、下一步、以及是否已同步。缺少证据时明确说“待验证”，不要补写记忆。
