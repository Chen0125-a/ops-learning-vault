# Dual-Memory Protocol

## Purpose

This protocol makes durable collaboration context portable across agents without pretending that different products share the same internal memory. Obsidian is the canonical cross-agent ledger. A documented agent-native memory is a local execution mirror/cache. The two stores cooperate, but they are not equal authorities.

The protocol preserves explicit state and learned working methods. It cannot preserve a model instance, hidden chain-of-thought, undocumented platform memory, inaccessible account data, or exact stochastic behavior.

## Normative terms

- **MUST** is required for a valid synchronization.
- **SHOULD** is the default unless current evidence gives a concrete reason to diverge.
- **MAY** is optional.

## Store roles

### Obsidian canonical ledger

Obsidian MUST contain every validated durable fact, stable preference, revisable collaboration impression, long-term decision, reusable lesson, active handoff, and durable environment fact that should survive switching agents. It MUST also contain the portable policy, Agent registry, provenance, status, and changelog.

### Agent-local mirror

An agent-native memory MUST be documented, accessible to the Agent or user, scoped deliberately, and proven by a real create/read/update round trip through the product's actual memory mechanism before it is registered as `verified`. File existence and operating-system write permission alone are insufficient. It SHOULD mirror the durable entries most useful to that Agent, using the same stable IDs and short summaries. It MAY also keep platform-specific operating details that have no cross-agent value.

A rule file is a behavior hook, not automatically a memory store. A chat transcript, session log, cache, database, hidden platform memory, or arbitrary workspace note MUST NOT be declared a native-memory store without evidence that the product uses it for durable memory.

## Session lifecycle

### 1. Pull before work

When durable user context matters, the Agent MUST:

1. discover the canonical package;
2. read the six core files in required order;
3. read `PORTABLE_MEMORY_POLICY.md`, `AGENT_MEMORY_REGISTRY.json`, and `PORTABILITY_MANIFEST.json`;
4. load only relevant domain context;
5. locate its own registry entry;
6. read relevant accessible local-memory entries if the entry is `verified`;
7. reconcile conflicts using the authority order below;
8. state missing, stale, or degraded layers briefly.

The Agent MUST NOT import an entire local memory file or old conversation merely because it exists.

### 2. Work with provenance

During the task, new observations remain candidates until supported. The Agent MUST distinguish:

- current primary evidence;
- explicit user confirmation or correction;
- validated durable entries;
- revisable impressions with evidence;
- unverified observations in `MEMORY_INBOX.md`.

### 3. Push before the final reply

Before every final reply, the Agent MUST perform a durable-delta audit. When nothing durable changed, it MUST write nothing to either store. When a durable change exists, it MUST:

1. update the narrowest canonical Obsidian file;
2. attach a stable ID, date, evidence/source, scope, and status;
3. append one compact `MEMORY_CHANGELOG.md` entry;
4. verify the canonical files are readable;
5. update the verified local mirror with the same changed IDs and concise summaries;
6. verify the local write through the product's documented method;
7. report any degraded or failed local sync honestly.

Obsidian MUST be written before the local mirror. A failed local write MUST NOT roll back or conceal a valid canonical update.

## Authority and conflict rules

Use this order:

1. current primary evidence or explicit user correction;
2. validated Obsidian entry;
3. agent-local memory;
4. unverified candidate or another agent's unsupported assertion.

The Agent MUST NOT use wall-clock recency alone as authority. If two validated entries conflict, preserve both, mark the older one superseded only when the evidence is sufficient, and link the replacement IDs. Material unresolved conflicts go to `MEMORY_INBOX.md` or to the user for clarification.

## Deduplication and loop prevention

- Stable IDs are the cross-store identity key.
- A mirror entry MUST retain the canonical stable ID rather than minting a second fact.
- Mirrored text MUST NOT return to Obsidian as a new observation.
- Repeated execution with no semantic change MUST be a no-op.
- `MEMORY_CHANGELOG.md` records canonical changes, not every read or mirror refresh.
- If a platform cannot retain stable IDs, its local store remains a convenience cache and MUST NOT be used for automatic reverse synchronization.

## Scope and privacy

The Agent MUST NOT store passwords, tokens, cookies, API keys, private keys, authentication artifacts, browser/account databases, complete chat transcripts, hidden reasoning, irrelevant private material, or sensitive terminal dumps. It MUST NOT convert a one-off tone, emotion, or temporary action into a permanent personality label.

Domain-only material stays in its domain package. It is promoted to general memory only when it is useful across themes. Platform-specific tool quirks MAY stay local unless another Agent would benefit from them.

## Status model

- `verified`: the policy is installed and every registered native-memory path is currently readable and writable.
- `degraded-no-native-memory-file`: the policy is installed, but no documented file-based native-memory mechanism is available. Obsidian continuity remains usable.
- `degraded-unverified-native-memory-path`: one or more declared native paths are missing or cannot be verified readable and writable.
- `degraded-unverified-native-memory-adapter`: a documented API or product adapter is known but has not passed a real write/read/update round trip.
- `degraded-unverified-rules-autoload`: native memory passed its round trip, but a fresh task has not proved that the persistent rule hook loads automatically.

`acceptance_status` is tracked separately. `pending-fresh-task-drill` means interfaces may be installed or individually verified but the complete inherited-context, warranted-update, and no-change drill has not passed. `verified` means that drill passed with evidence.

Never use `verified` merely because the Agent product advertises memory. Verification requires evidence for the actual interface recorded in the registry.

## Recovery behavior

If the local mirror is lost, rebuild it from Obsidian through the Agent's documented memory mechanism. If Obsidian is temporarily unavailable, the Agent MAY use local memory for limited work but MUST label it potentially stale and MUST NOT promote local-only assertions automatically when the vault returns. If both stores are unavailable, the Agent MUST report that continuity is unavailable.
