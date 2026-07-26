# Memory Lifecycle and Selective Loading

## Purpose

Prevent durable memory from anchoring an Agent to obsolete conclusions, consuming an ever-growing context window, or turning a temporary interaction into a permanent user label. `MEMORY_INDEX.json` is a generated routing and health artifact beside the canonical Markdown files. It never outranks or replaces those files.

## Write gate

A proposed memory item MUST pass all applicable checks before promotion:

1. **Durability**: it is likely to matter in a later task, not merely in the current conversation.
2. **Usefulness**: a future Agent can act differently or avoid a known failure because of it.
3. **Evidence**: it cites an explicit user statement, reproducible result, or multiple independent observations.
4. **Scope**: it states where it applies; domain-only knowledge stays in the domain package.
5. **Safety**: it contains no secret, full transcript, hidden reasoning, irrelevant private data, or sensitive unsupported inference.
6. **Non-duplication**: an existing stable ID is revised or superseded when appropriate.

When any check is uncertain, place the observation in `MEMORY_INBOX.md` as `candidate`; do not load it as an established fact.

User impressions have an additional gate. One interaction is never enough for an active impression. Promotion requires at least two independent evidence points, a narrow falsifiable wording, a review date, and an explicit statement that newer evidence may revise it. Directly stated user preferences are facts/preferences, not inferred impressions, but still require scope and review.

## Lifecycle states

Each indexed entry has two independent dimensions:

- `status`: `active`, `candidate`, `review-due`, `superseded`, or `archived`;
- `tier`: `hot`, `warm`, `cold`, or `archive`.

Meaning:

| Status | Routine authority | Required action |
|---|---|---|
| `active` | usable if its review date has not passed | load by tier and relevance |
| `candidate` | hypothesis only | seek evidence; never treat as fact |
| `review-due` | withheld from routine context | revalidate, revise, supersede, or archive |
| `superseded` | historical only | retain replacement link in Markdown |
| `archived` | historical only | retain for audit; do not routinely load |

| Tier | Loading rule |
|---|---|
| `hot` | load for ordinary continuity while active, fresh, and within budget |
| `warm` | load only when the current task query matches its title, summary, scope, or activation terms |
| `cold` | load only during explicit research, candidate review, audit, or full-mode work |
| `archive` | exclude from ordinary work; load only for history or conflict investigation |

No command automatically deletes memory. Expiry means “stop trusting automatically and review,” not “erase.”

## Default review cadence

The index builder supplies conservative defaults when the Markdown entry has no explicit lifecycle metadata:

- candidate observation: 30 days;
- collaboration impression: 60 days;
- environment fact: 90 days;
- ordinary fact, preference, or lesson: 180 days;
- explicit durable decision: 365 days;
- `CURRENT.md`: stale after 14 days without review.

Explicit evidence may justify a different date. Stable identity facts can use a long review interval, but no inferred impression is permanent. A passed `review_after` date causes routine loading to exclude the entry even if its stored status still says `active`; the source Markdown is then updated during maintenance to make the state explicit.

## Routine mode

Use routine mode for ordinary tasks that need user context but do not change memory:

```text
python scripts/continuity.py memory-health --vault <vault>
python scripts/continuity.py runtime-context --vault <vault> --query <current-task> --max-chars 12000
```

The runtime command MUST fail closed when source fingerprints do not match. Its output contains `CURRENT.md`, eligible hot entries, and relevant warm entries only. It excludes candidates, due entries, superseded entries, and archives. The caller SHOULD briefly disclose stale `CURRENT.md`, due records, budget skips, or a degraded local mirror.

## Full mode

Read the six canonical memory files completely, followed by policy, registry, manifest, inbox, changelog as needed, when any of these applies:

- migration, restore, onboarding, or acceptance testing;
- durable memory write or correction;
- stale, missing, invalid, or oversized index;
- conflict, provenance investigation, privacy audit, or lifecycle maintenance;
- user explicitly requests a full memory audit.

Full mode is a maintenance and recovery path, not the default context payload for every task.

## Safe update transaction

For a warranted durable change:

1. enter full mode and reconcile current evidence;
2. update the narrowest canonical Markdown source using a stable ID, evidence, scope, status, and review date;
3. append the changed IDs and files to `MEMORY_CHANGELOG.md`;
4. rebuild the index atomically:

```text
python scripts/continuity.py build-index --vault <vault> --apply
```

5. run `memory-health`; resolve structural or fingerprint errors before finalizing;
6. update a verified Agent-local mirror with compact ID-based summaries;
7. verify the local round trip or report the exact degraded status.

The source Markdown plus changelog are the durable record. The index is regenerated after them. Never hand-edit a source fingerprint to conceal drift.

## Health interpretation

`memory-health` separates blocking errors from review warnings:

- blocking: missing/invalid index, source fingerprint drift, duplicate IDs, invalid status/tier, invalid budget;
- warning: review-due entry, overdue candidate, under-evidenced active impression, stale `CURRENT.md`, hot context over budget.

Blocking errors prohibit selective loading. Warnings do not erase data; they narrow what may be trusted and create maintenance work. If the hot set exceeds budget, demote the least universal items to warm, shorten summaries, or supersede obsolete entries after evidence review.

## Index contract

`MEMORY_INDEX.json` schema version `1` contains:

- SHA-256 fingerprints for `CURRENT.md`, the five durable ledgers, `ENVIRONMENT.md`, and `MEMORY_INBOX.md`;
- an explicit hot-character budget;
- lifecycle policy flags, including `automatic_delete: false`;
- one entry per stable ID with source, title, summary, status, tier, scope, activation terms, confirmation date, review date, and evidence count.

Rebuilding preserves reviewed lifecycle metadata for an existing stable ID while refreshing source-derived title, summary, status, and fingerprints. A source status of superseded or archived always forces the archive tier.
