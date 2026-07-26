# Continuity Architecture

## Contents

- Recovery promise
- Five continuity layers
- Dual-memory authority
- Source separation
- Skill inventory classes
- Failure model

## Recovery promise

The system restores explicit, inspectable collaboration state. It can make a new agent behave consistently with recorded preferences and workflows, but it cannot recreate a particular model process or any state that was never written down.

Use four confidence labels in restoration reports:

- **Verified**: present, readable, checksum-valid, and supported by current evidence.
- **Restored**: copied or installed successfully, but not yet exercised by the target agent.
- **Planned**: source or reinstall recipe is known, but the target action has not run.
- **Unavailable**: absent, intentionally excluded, or impossible to export.

Never collapse these labels into a single success claim.

## Five continuity layers

| Layer | Source of truth | Examples | Restore test |
|---|---|---|---|
| Semantic memory | Obsidian Markdown ledgers plus generated lifecycle index | facts, preferences, decisions, lessons | new agent validates fingerprints and retrieves the right bounded context |
| Active state | Obsidian `CURRENT.md` and domain `CURRENT.md` | priorities, blockers, next step | agent identifies the current handoff without old chat |
| Behavior | portable rules | privacy, evidence, audit, teaching trigger | agent follows a reversible probe task correctly |
| Capabilities | Skill sources and managed-source inventory | custom Skills, catalog Skills | required Skill triggers and its validator passes |
| Environment | verified inventory | paths, tools, resource limits, repositories | current read-only checks confirm or supersede history |

Account sessions, credentials, platform databases, hidden prompts, hidden reasoning, stochastic style, and unrecorded conversations are outside the boundary.

## Dual-memory authority

The semantic-memory layer has two implementations with different roles:

- Obsidian is the canonical, portable ledger shared by every Agent.
- A documented Agent-native memory is a local mirror/cache for faster product-specific continuity.

This is intentionally asymmetric. Equal peers create last-writer-wins corruption, duplicate facts, and sync loops. Every session pulls canonical context before work. Every durable update writes Obsidian first, records stable IDs and provenance, then mirrors those IDs locally. A missing local store degrades convenience but does not invalidate canonical continuity.

Canonical does not mean “load everything every time.” `MEMORY_INDEX.json` is a disposable routing layer with source hashes, lifecycle state, tiers, review dates, evidence counts, and a hot-context budget. Routine work uses it to load current plus relevant memory. Full canonical reads are reserved for writes, migration, restore, audit, conflict resolution, and stale-index recovery. Markdown remains authoritative; any hash mismatch disables selective loading until the index is rebuilt.

Persistent Agent rules are the automatic lifecycle hook. They tell the Agent to invoke this Skill at context load and before its final reply. The actual local-memory adapter remains product-specific and must be verified rather than guessed.

## Source separation

Maintain three independent channels:

1. Obsidian holds user-specific memory and domain context.
2. Each Agent may hold a local mirror plus an automatically loaded policy block; the Agent registry records only verified interfaces.
3. A reviewed Skill distribution holds portable procedural code without personal data.
4. A continuity bundle joins explicit allowlisted context and user-owned Skills for a user-initiated migration or backup.

Routine durable changes update Obsidian first and then a verified local mirror. Skill publishing and continuity backup are explicit tasks with separate destinations and privacy review; neither happens during routine memory synchronization.

Bundle SHA-256 checksums detect corruption and changes relative to a trusted checksum file. They are not signatures and do not authenticate the bundle's author. Use a trusted transfer channel or a separately verified signature when adversarial tampering is in scope.

## Skill inventory classes

### User-owned portable

Copy the full source directory. Preserve scripts, references, assets, tests, metadata, and version information. Require a valid `SKILL.md` and scan the whole exported directory.

### Managed or reinstallable

Record provider, package/plugin identifier, repository or catalog, and version/ref. Prefer reinstalling because copied caches can be incomplete or unsafe. If origin is unknown, mark the Skill unresolved.

When unresolved Skill source is still required for continuity, preserve the current complete source folder in an explicitly labeled, checksummed `local-inventory` bundle group. Report the upstream provenance as unresolved even when the local source restores successfully.

### Platform or generated

Exclude system Skills, authentication, caches, plugin caches, sessions, logs, virtual environments, dependency trees, and generated state. The target platform recreates these.

## Failure model

Treat any of these as an incomplete migration:

- a required memory or domain file is missing;
- a required custom Skill lacks source or a verified reinstall path;
- a checksum fails or an unexpected file appears;
- an existing target file conflicts;
- portable rules were copied without semantic merge;
- an Agent is called dual-memory verified without an accessible documented native-memory interface;
- a local-memory entry overwrites canonical Obsidian data without conflict resolution;
- a mirrored entry is re-imported under a new ID and creates a sync loop;
- the target agent cannot distinguish confirmed facts from impressions or candidates;
- the lifecycle index is missing/stale, an expired entry remains routine authority, or hot memory exceeds its declared budget without disclosure;
- a one-off inferred impression is promoted without two independent evidence points and a review date;
- an export contains credential indicators;
- the restore has not been exercised in a new-context drill.

Prefer a partial result labeled honestly over an unsafe or unverifiable “complete” result.
