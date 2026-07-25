---
name: obsidian-user-memory
description: Load, maintain, audit, migrate, and verify the user's portable collaboration memory stored in an Obsidian vault. Use when a new Codex account or device must restore context; when the user asks Codex to remember, update, correct, export, back up, or sync durable facts, preferences, impressions, decisions, lessons, environment facts, or agreed conclusions; and before the final reply of a conversation that produced such long-term changes. Keep routine memory writes local to Obsidian and perform Git operations only when the user explicitly requests them.
---

# Obsidian User Memory

Treat the Obsidian package as an external, user-owned fact source. Do not claim to restore model internals, hidden reasoning, login state, or unrecorded chat history.

## Locate the package

1. Use a path explicitly supplied by the user.
2. Otherwise search the current workspace and its parents for `AI协作-通用记忆包/README.md`.
3. On this Windows setup, try `D:\笔记\AI协作-通用记忆包\README.md`.
4. If still missing, run `scripts/find_memory_root.ps1` or ask for the vault path. Do not create a second package until existing locations have been checked.

Set the package root to the directory containing `README.md`. Treat paths stored in memory as historical until a current read-only check confirms them.

## Load context

Read these files completely in order:

1. `CURRENT.md`
2. `USER_PROFILE.md`
3. `COLLABORATION_MEMORY.md`
4. `DECISIONS.md`
5. `LESSONS.md`
6. `ENVIRONMENT.md`

Read `MEMORY_INBOX.md` only when resolving candidate observations or maintaining memory. Read `MEMORY_CHANGELOG.md` when checking freshness or auditing a migration.

If the task concerns the three-month operations-internship course, additionally load the teacher package, learning profile, plan, daily questions, and due mistake reviews referenced by the vault `AGENTS.md`. Do not copy course-only details into the general package.

After loading, briefly confirm the package path and last review date. Summarize only the context relevant to the current task; do not dump the full profile unless requested.

## Resolve conflicts

- Prefer current primary evidence and explicit user corrections over stored memory.
- Distinguish confirmed facts from evidence-based impressions and unverified inbox items.
- Never silently rewrite history. Mark replaced entries `已废弃`, name the replacement ID, and explain the evidence.
- Ask only if a conflict would materially change the requested outcome and cannot be resolved from local evidence.

## Audit before the final reply

Decide whether the conversation changed any durable information:

- confirmed user fact or stable preference → `USER_PROFILE.md`
- evidence-based, reusable collaboration method → `COLLABORATION_MEMORY.md`
- explicit long-term choice or boundary → `DECISIONS.md`
- reusable correction or agreed correct conclusion → `LESSONS.md`
- durable device, path, tool, or repository fact → `ENVIRONMENT.md`
- active priority, handoff, blocker, or next step → `CURRENT.md`
- plausible but unconfirmed observation → `MEMORY_INBOX.md`

If nothing durable changed, make no file edit. If something changed:

1. Update the narrowest relevant file before sending the final reply.
2. Include date, source/evidence, scope, status, and a stable ID.
3. Append one compact entry to `MEMORY_CHANGELOG.md` naming changed IDs and files.
4. Update `reviewed` only on files actually reviewed or changed.
5. For teaching-only changes, update the teacher package instead; update both only when a conclusion truly applies across topics.
6. Stop after the Obsidian files are verified. Do not run `git add`, commit, push, or any remote sync as part of a routine end-of-conversation audit.

## Privacy and quality gate

Never store passwords, tokens, cookies, API keys, private keys, authentication files, browser data, full chats, unrelated personal data, sensitive terminal dumps, or hidden chain-of-thought. Do not infer personality, motive, health, finances, relationships, or ability from a single interaction. Store a collaboration impression only when it affects future work, has concrete evidence, is labeled as revisable, and is not a sensitive inference.

Do not promote a statement merely because an earlier AI wrote it. Require user confirmation, repeat evidence, or a reproducible result.

## Install or migrate

1. Distribute this Skill independently from the user's memory data. The GitHub copy contains only `SKILL.md`, `agents/`, and `scripts/`; it must not bundle profile, decisions, changelog, teaching records, or other vault content.
2. Transfer or sync the Obsidian vault through the user's chosen storage method. GitHub installation of the Skill does not restore the memory data by itself.
3. Install the Skill in the new machine's user Skill directory, normally `%USERPROFILE%\.codex\skills\obsidian-user-memory\`.
4. Merge the portable memory rule into the new user-level `AGENTS.md`; preserve unrelated existing rules.
5. Run `scripts/verify_memory_package.ps1 -VaultPath <vault>` and fix every required-file failure.
6. Invoke `$obsidian-user-memory`, supply the vault path when auto-discovery cannot find it, and perform a read-only context check.

## Optional Git sync

Perform Git operations only after an explicit user request for a Skill release or a separately approved backup:

- For a Skill release, stage and publish only this Skill's source files. Do not stage the Obsidian memory files.
- For a memory backup, treat it as a separate privacy-reviewed operation with an exact destination and scope; never infer it from a routine memory update.
- Inspect the exact diff, check for credentials or bundled personal data, and avoid unreviewed blanket staging.
- If authentication fails, retain local work and report the authorization step without exposing credentials.

## Completion criteria

For a routine conversation, finish when the necessary Obsidian files are updated and readable; Git status is irrelevant. Declare restoration complete only when the package is found, all required files are readable, this Skill validates, and the user-level installation is present. For an explicitly requested Skill release or backup, also report the Git result and any unverified external state.
