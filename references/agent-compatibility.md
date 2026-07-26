# Agent Compatibility

## Contents

- Universal protocol
- Native Skill targets
- Non-native targets
- Adapter discovery
- Rule adaptation
- Acceptance drill

## Universal protocol

Every target agent must be able to read Markdown and JSON, access the restored vault, and report file evidence. The continuity protocol is independent of any model vendor:

1. Verify the bundle or package.
2. Read this `SKILL.md` completely.
3. Read the six core memory files in order.
4. Read the portability manifest and only the domain context relevant to the task.
5. Read the portable memory policy and locate the Agent's registry entry.
6. Apply the authority, privacy, evidence, conflict, and end-of-conversation audit rules.
7. Report unavailable capabilities instead of improvising them.

## Native Skill targets

If the target supports folders containing `SKILL.md`, install the complete folder in its documented user Skill directory. Keep `agents/openai.yaml` as Codex UI metadata; another agent may ignore it. Test the actual trigger after installation.

Do not assume installation paths from the old machine. Discover the target's current documented path or ask the target agent to identify it.

## Non-native targets

If the target does not support Skills:

1. Present `SKILL.md` as the operating protocol.
2. Present `HANDOFF.md` from the verified bundle.
3. Supply the restored vault root.
4. Ask the agent to confirm the recovery boundary and summarize the six core files.
5. Store only the smallest adapter instruction supported by that product.

This preserves semantics even when automatic triggering is unavailable.

## Adapter discovery

Before running `bootstrap-agent`, discover four capabilities independently:

| Capability | Required evidence | If unavailable |
|---|---|---|
| Skill installation | documented user Skill location or a successful trigger test | present `SKILL.md` manually |
| Persistent rules | documented file/instruction mechanism and fresh-task autoload test | invoke the protocol explicitly every task |
| Native memory | documented readable/writable file or API and round-trip verification | register no native path; use degraded mode |
| Vault access | current read and write test against the restored package | stop memory writes and report the blocker |

Do not infer a native memory file from a familiar filename. `MEMORY.md`, `AGENTS.md`, project notes, and session data mean different things in different products. Record the actual verified path and scope in `AGENT_MEMORY_REGISTRY.json`.

Use a stable `agent_id` scoped to the adapter contract, for example a product plus profile type. Do not include account email, machine serial, token, or other sensitive identifiers.

## Rule adaptation

Map intent, not filenames:

- global/user rules → the target's persistent user-instruction mechanism;
- project rules → the target's project instruction file;
- Skill triggers → native Skill metadata if available, otherwise explicit invocation examples;
- tool-specific commands → equivalent current tools, with unsupported actions reported.
- local-memory synchronization → the target's documented memory interface; if it cannot retain stable IDs, use it only as a one-way convenience mirror.

Always merge portable rules with existing target rules. Never overwrite unrelated instructions or weaken higher-priority safety rules.

## Acceptance drill

Use a fresh task with no old chat context and ask the target agent to:

1. identify the current priority;
2. state two stable collaboration preferences and their evidence status;
3. distinguish a confirmed fact from an impression and an inbox candidate;
4. name the relevant domain package for a teaching request;
5. list required custom Skills and any missing source;
6. propose one reversible action using current environment evidence;
7. explain when it would and would not update memory;
8. perform one warranted update and show that Obsidian changed before the local mirror;
9. complete one no-change conversation without adding entries;
10. identify its registry status and any degraded layer;
11. confirm it did not restore credentials, hidden reasoning, or account state.

Pass only when the answers trace to current files, stable IDs do not duplicate across stores, and no unavailable layer is described as restored.
