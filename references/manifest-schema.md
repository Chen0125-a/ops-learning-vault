# Portability Manifest Schema

## Contents

- Location and encoding
- Required fields
- Memory protocol and Agent registry
- Context entries
- Skill inventory
- Example

## Location and encoding

Store `PORTABILITY_MANIFEST.json` in the general memory package. Encode it as UTF-8 JSON. Paths under `context_paths` are relative to the Obsidian vault root and must not contain `..` or an absolute prefix.

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | integer | `4` for lifecycle-aware packages; `3` remains readable for restore compatibility |
| `package_id` | string | Stable identifier for this continuity package |
| `memory_package` | string | General memory directory name |
| `context_paths` | array | Explicit vault content allowed into a migration bundle |
| `required_skills` | array of strings | User capabilities that must be recoverable |
| `managed_skill_sets` | array | Reinstallable collections and their provenance |
| `memory_protocol` | object | Canonical store, policy, Agent registry, and sync ordering |
| `last_verified` | `YYYY-MM-DD` string | Date of the last complete continuity audit |

## Memory protocol and Agent registry

For schema version `4`, `memory_protocol` must contain these exact invariants:

```json
{
  "canonical_store": "obsidian",
  "policy": "AI协作-通用记忆包/PORTABLE_MEMORY_POLICY.md",
  "agent_registry": "AI协作-通用记忆包/AGENT_MEMORY_REGISTRY.json",
  "lifecycle_index": "AI协作-通用记忆包/MEMORY_INDEX.json",
  "runtime_loading": "selective-index",
  "sync_order": ["pull-before-work", "push-before-final-reply"]
}
```

Schema version `3` retains the four original fields and can still be verified or restored, but it does not claim lifecycle-aware selective loading. Upgrade it before using `build-index`, `memory-health`, or routine selective context as the continuity contract.

`MEMORY_INDEX.json` uses schema version `1`. It is generated from the canonical Markdown ledgers and contains source fingerprints, a hot-context character budget, non-destructive lifecycle policy, and stable-ID entries with title, source, summary, status, tier, scope, activation terms, confirmation date, review date, and evidence count. It is a routing/cache artifact, not a new authority. A fingerprint mismatch blocks selective loading and requires a full read plus atomic rebuild.

`AGENT_MEMORY_REGISTRY.json` uses schema version `1`, declares `canonical_store` as `obsidian`, and stores an `agents` array. Each Agent entry requires:

- `agent_id`: stable non-sensitive ID matching letters, digits, dot, underscore, or hyphen;
- `product`: human-readable product name;
- `rules_file`: documented persistent-rule target; automatic loading is tracked separately;
- `rules_autoload`: `verified` or `pending-fresh-task-verification`;
- `rules_autoload_evidence`: non-empty evidence describing the fresh-task result or why it is pending;
- `native_memory_paths`: explicit readable/writable memory files, or an empty list;
- `native_memory_mode`: `file-mirror`, `api-adapter`, or `unavailable-or-unverified`;
- `native_memory_adapter`: required non-secret adapter reference when a verified API adapter is used;
- `native_memory_status`: the native interface result before rule-autoload status is considered;
- `native_memory_verification`: object containing `status`, `method`, and `evidence`; `verified` requires a real create/read/update round trip, not an OS permission check;
- `dual_memory_status`: `verified`, `degraded-no-native-memory-file`, `degraded-unverified-native-memory-path`, `degraded-unverified-native-memory-adapter`, or `degraded-unverified-rules-autoload`;
- `acceptance_status`: `verified` or `pending-fresh-task-drill`;
- `sync_trigger`: must be `before-final-reply`;
- `last_verified`: verification date.

Store home-relative paths as `~/...` when possible. Never put credentials, account identifiers, opaque platform databases, or guessed paths in the registry.

## Context entries

Each entry contains:

- `path`: vault-relative file or directory;
- `role`: `general-memory`, `domain-memory`, `portable-rules`, `learning-record`, or another clear role;
- `required`: whether absence blocks a complete export;
- `activate_when`: optional natural-language condition for loading the context.

Keep the allowlist narrow. Including a directory exports everything below it except denied system/cache directories, so prefer the smallest coherent fact source.

## Skill inventory

`required_skills` names capabilities, not installation paths. During audit, supply current user Skill roots. During export, label each root, for example `codex-user` or `agent-user`. The bundle preserves those labels so restoration maps each group to an explicit target root.

Describe managed collections in `managed_skill_sets` with:

- `name`;
- `source_type`: `catalog`, `plugin`, `repository`, `package`, or `local-inventory`;
- `source` and optional `version`/`ref`;
- `restore`: exact reinstall method or a statement that manual reinstall is required;
- `required`: whether absence blocks functional continuity.
- `inventory`: every Skill name covered by this source; names may not appear in two sets.
- `bundle_group`: required for `local-inventory`, naming the migration group that preserves source when upstream provenance is unavailable.

Use `local-inventory` only as an explicit fallback. Add `provenance_status` to state what is still unknown. A complete migration can preserve those Skill sources in a checksummed bundle, but it must not pretend their upstream origin or version has been verified.

Do not place credentials, private repository tokens, or authenticated URLs in the manifest.

## Example

```json
{
  "schema_version": 4,
  "package_id": "portable-agent-continuity",
  "memory_package": "AI协作-通用记忆包",
  "context_paths": [
    {
      "path": "AI协作-通用记忆包",
      "role": "general-memory",
      "required": true
    },
    {
      "path": "AGENTS.md",
      "role": "portable-rules",
      "required": true
    },
    {
      "path": "求职/运维实习-教师包",
      "role": "domain-memory",
      "required": true,
      "activate_when": "The task concerns the operations internship course"
    }
  ],
  "required_skills": [
    "obsidian-user-memory",
    "yunwei-teacher"
  ],
  "managed_skill_sets": [],
  "memory_protocol": {
    "canonical_store": "obsidian",
    "policy": "AI协作-通用记忆包/PORTABLE_MEMORY_POLICY.md",
    "agent_registry": "AI协作-通用记忆包/AGENT_MEMORY_REGISTRY.json",
    "lifecycle_index": "AI协作-通用记忆包/MEMORY_INDEX.json",
    "runtime_loading": "selective-index",
    "sync_order": [
      "pull-before-work",
      "push-before-final-reply"
    ]
  },
  "last_verified": "2026-07-26"
}
```
