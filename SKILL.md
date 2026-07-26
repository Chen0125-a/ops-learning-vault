---
name: obsidian-user-memory
description: Preserve, synchronize, audit, export, restore, and verify portable user collaboration continuity through an Obsidian canonical ledger plus each agent's documented local-memory mechanism. Use when switching among Codex or other AI agents; when a new account, computer, or agent must inherit durable facts, preferences, evidence-based collaboration impressions, decisions, lessons, active handoff, environment facts, domain memory packages, portable rules, and user-owned Skills; when onboarding an agent's persistent rule or memory files; when the user asks to remember, correct, migrate, back up, restore, or test continuity; and before the final reply of a conversation that produced durable changes. Keep Obsidian authoritative, treat agent-local memory as a mirror/cache, exclude credentials and platform internals, default restoration and onboarding to read-only/dry-run, never invent unsupported native memory, and perform Git or remote sync only when explicitly requested.
---

# Obsidian User Memory and Agent Continuity

Reconstruct explicit collaboration continuity from user-owned artifacts and keep it synchronized across agents. Never claim to restore the exact model instance, hidden reasoning, unrecorded chats, inaccessible platform-side memory, authentication, or stochastic behavior. Restore the documented working relationship: facts, preferences, decisions, verified methods, active state, rules, Skills, and evidence history.

## Use the four-layer model

1. **Obsidian canonical layer**: Treat the vault as the cross-agent source of truth for personal memory, domain packages, the Agent registry, and the portability manifest.
2. **Agent-local mirror layer**: Use only a documented, accessible native-memory mechanism. Reconcile it against Obsidian at task start and mirror validated deltas after Obsidian is updated. It never outranks the canonical ledger.
3. **Behavior layer**: Install the portable memory policy into the target's automatically loaded persistent rules by semantic merge; never overwrite unrelated content.
4. **Capability layer**: Preserve user-owned Skill source; record managed Skills by origin/version and reinstall them instead of copying caches or platform internals.

Keep these layers independently replaceable. Installing this Skill alone does not restore absent vault data. Restoring the vault alone does not install Skills or activate agent rules. An agent without a verified native-memory file still receives full continuity from Obsidian, but its status is degraded rather than “dual-memory synchronized.”

Always read [memory-lifecycle.md](references/memory-lifecycle.md) before loading, reviewing, or writing memory, and read [dual-memory-protocol.md](references/dual-memory-protocol.md) before onboarding or reconciling stores. For architecture and recovery guarantees, read [continuity-architecture.md](references/continuity-architecture.md). For the manifest, index, and registry contract, read [manifest-schema.md](references/manifest-schema.md). When onboarding a new target or working outside Codex, read [agent-compatibility.md](references/agent-compatibility.md).

## Locate the package

Use an explicit path first. Otherwise run:

```text
python scripts/continuity.py discover
```

Discovery checks `OBSIDIAN_MEMORY_VAULT`, the current directory and parents, common Obsidian locations, and the known Windows location. Do not create a second memory package until the existing vault has been checked.

Set the package root to the directory containing `README.md`, `CURRENT.md`, and `COLLABORATION_MEMORY.md`. Treat stored paths as historical until a current read-only check confirms them.

## Load context

Choose a loading mode before reading personal memory.

For an ordinary task, first run:

```text
python scripts/continuity.py memory-health --vault <vault>
python scripts/continuity.py runtime-context --vault <vault> --query <current-task> --max-chars 12000
```

Use the bounded runtime output: current handoff, active fresh hot memory, and query-relevant warm memory. Do not routinely load candidates, review-due entries, superseded entries, or archives. If the index is missing, stale, invalid, or over budget, stop selective loading and use full mode.

Use full mode for migration, restore, onboarding, acceptance tests, conflict resolution, privacy or lifecycle audit, every durable memory write, or any index failure. Read completely and in order:

1. `CURRENT.md`
2. `USER_PROFILE.md`
3. `COLLABORATION_MEMORY.md`
4. `DECISIONS.md`
5. `LESSONS.md`
6. `ENVIRONMENT.md`

Then read `PORTABLE_MEMORY_POLICY.md`, `AGENT_MEMORY_REGISTRY.json`, `PORTABILITY_MANIFEST.json`, and validate `MEMORY_INDEX.json` against its sources. Load additional `context_paths` only when their activation condition matches the task. Read `MEMORY_INBOX.md` while resolving candidate observations or maintaining memory. Read `MEMORY_CHANGELOG.md` when auditing freshness, migration, restoration, or a suspected sync gap.

If the current agent has a registry entry and its native-memory paths are accessible, read only the relevant local entries and reconcile them against Obsidian. Do not bulk-copy a full local memory file or chat history into the vault. If the agent is absent from the registry, run the onboarding workflow before claiming automatic continuity.

Briefly report the package path, last review date, relevant active context, and any missing or stale layer. Do not dump the full profile unless asked.

## Resolve evidence and conflicts

- Prefer current primary evidence and explicit user corrections over stored memory.
- Distinguish confirmed facts, evidence-based impressions, active handoff, and unverified inbox observations.
- Never silently rewrite history. Mark replaced entries `已废弃`, name the replacement ID, and cite the evidence.
- Treat another AI's assertion as unverified unless the user confirmed it or reproducible evidence supports it.
- Ask only when an unresolved conflict materially changes the requested outcome.

Use this authority order for every cross-store conflict:

1. current primary evidence or explicit user correction;
2. validated Obsidian entry;
3. agent-local memory;
4. unverified inbox candidate or another agent's unsupported assertion.

Quarantine unresolved conflicts in `MEMORY_INBOX.md`; do not create a last-writer-wins loop.

## Audit before the final reply

Classify durable changes narrowly:

- confirmed user fact or stable preference → `USER_PROFILE.md`
- reusable collaboration method → `COLLABORATION_MEMORY.md`
- explicit long-term choice or boundary → `DECISIONS.md`
- reusable correction or agreed conclusion → `LESSONS.md`
- durable device, path, tool, or repository fact → `ENVIRONMENT.md`
- active priority, handoff, blocker, or next step → `CURRENT.md`
- plausible but unconfirmed observation → `MEMORY_INBOX.md`

If nothing durable changed, make no memory edit. If something changed:

1. Enter full mode and apply the write gate in `memory-lifecycle.md`.
2. Update the narrowest relevant file before the final reply.
3. Include date, source/evidence, scope, status, review date, and a stable ID. An inferred user impression needs two independent evidence points before `active`; otherwise keep it as a candidate.
4. Append a compact entry to `MEMORY_CHANGELOG.md` naming changed IDs and files.
5. Update `reviewed` only on files actually reviewed or changed.
6. Write domain-only changes to their domain package; promote them to general memory only when they apply across topics.
7. Rebuild `MEMORY_INDEX.json` atomically with `build-index --apply`, then run `memory-health`. Never edit a fingerprint to mask source drift.
8. Verify the Obsidian files are readable.
9. If the current registry entry names verified readable and writable native-memory files, update them through that agent's documented mechanism with a compact mirror containing the changed stable IDs, short summaries, canonical package location, and sync date.
10. Re-read the affected native-memory section or use the platform's documented verification method. Never mirror secrets, complete chats, hidden reasoning, or unsupported inferences.
11. If native-memory sync is unavailable or fails, keep the successful Obsidian update, record/report the degraded status, and do not claim dual-memory success.
12. Stop. Do not run Git or remote sync as part of routine memory maintenance.

Always write Obsidian first and the local mirror second. Local memory must not write its own mirrored text back into Obsidian as a new fact; stable IDs and source metadata prevent duplicate loops.

## Onboard this agent once

On first use in each Agent product or installation:

1. Identify, from current documentation or direct read-only evidence, the user-level rules file that the Agent automatically loads. Do not guess a path.
2. Identify any documented, user-readable and user-writable native-memory file or API. A workspace note, chat transcript, cache, session database, or opaque platform memory is not automatically a valid native-memory store.
3. Choose a stable `agent_id` for that product and memory scope. Reuse it on another computer only when the same portable rule and memory contract applies.
4. Preview the semantic rule merge:

```text
python scripts/continuity.py bootstrap-agent \
  --vault <vault> \
  --agent-id <stable-agent-id> \
  --product <product-name> \
  --rules-file <documented-auto-loaded-rules-file> \
  [--native-memory <verified-readable-writable-memory-file>] \
  [--native-memory-adapter <non-secret-adapter-id>]
```

5. If the preview reports no conflict, repeat with `--apply`. The command preserves unrelated rules, installs one marked policy block, and records pending verification in `AGENT_MEMORY_REGISTRY.json` idempotently.
6. If a marked policy block differs, stop for semantic review. Never replace it blindly.
7. Open a fresh task and prove that the rules load automatically. For a file or API memory adapter, complete a real create/read/update round trip through the product's documented mechanism.
8. Re-run `bootstrap-agent --apply` with `--confirm-rules-autoload` and, only when that native-memory round trip passed, `--confirm-native-memory-roundtrip`.
9. Complete the full drill in [agent-compatibility.md](references/agent-compatibility.md), including one warranted memory update and one no-change conversation; then re-run with `--confirm-acceptance-drill` plus the already proven confirmation flags.

Use either file paths or an API adapter, never both. A path being present and writable is only a precondition; it does not prove that the product consumes it. `--confirm-native-memory-roundtrip`, `--confirm-rules-autoload`, and `--confirm-acceptance-drill` are evidence declarations made after the corresponding real tests, never substitutes for testing. If native memory is proprietary, inaccessible, undocumented, or absent, omit both native-memory options; use Obsidian as the working memory and report `degraded-no-native-memory-file`.

## Classify Skills before migration

Inventory every configured Skill and assign exactly one class:

- **User-owned portable**: authored or customized for the user. Export the complete Skill folder, including `SKILL.md`, `agents/`, scripts, references, assets, and tests.
- **Managed/reinstallable**: installed from a catalog, plugin, package, or known repository. Record the exact source and version/ref; prefer reinstalling from that source. Export source only when the source cannot be recovered.
- **Platform/system**: bundled with the agent runtime, plugin cache, authentication, session store, or generated cache. Never copy it as user continuity.

Require `SKILL.md` for every exported Skill. Exclude `.system`, plugin caches, `.git`, `.obsidian`, dependency caches, virtual environments, and generated caches. If provenance is uncertain, mark it unresolved in the audit instead of guessing.

## Run a readiness audit

Use read-only verification before export or after restoration:

```text
python scripts/continuity.py verify --vault <vault> --skill-root <user-skill-root> [--skill-root <another-root>]
```

Also run `memory-health --vault <vault>`. Treat missing core files, a missing/stale lifecycle index, `PORTABLE_MEMORY_POLICY.md`, `AGENT_MEMORY_REGISTRY.json`, required context, required Skills, invalid manifest or registry data, symlinks, forbidden filenames, or high-confidence credential patterns as failures. Review warnings—expired records, overdue candidates, weak impressions, stale current state, or an oversized hot set—before claiming lifecycle health. A green audit establishes artifact integrity, not literal identity continuity.

## Export a continuity bundle

Export only after the user asks for migration or backup and an exact destination is known:

```text
python scripts/continuity.py export \
  --vault <vault> \
  --output <new-empty-destination> \
  --skill-root codex-user=<user-skill-root> \
  [--skill-root another-agent=<another-user-skill-root>]
```

The export must:

1. Read the allowlisted `context_paths` from `PORTABILITY_MANIFEST.json`.
2. Include all valid top-level Skills from explicitly supplied user Skill roots.
3. Fail closed on credentials, secret-bearing filenames, private-key markers, symlinks, missing required assets, or an existing output path.
4. Avoid absolute source paths in the bundle manifest.
5. Create `bundle-manifest.json`, `HANDOFF.md`, and `checksums.sha256`.
6. Leave the source vault and Skill roots unchanged.

Do not publish or sync the bundle merely because it exists. Storage, encryption, and remote destination are separate user decisions.

Treat SHA-256 as corruption and post-creation change detection, not proof of publisher identity. Authenticity requires a trusted transfer channel or a separately verified signature.

## Restore safely

Verify first:

```text
python scripts/continuity.py verify-bundle --bundle <bundle>
```

Preview restoration without writes:

```text
python scripts/continuity.py restore \
  --bundle <bundle> \
  --target-vault <target-vault> \
  --skill-target codex-user=<target-skill-root>
```

Apply only after the preview is clean:

```text
python scripts/continuity.py restore <same-arguments> --apply
```

Never overwrite a different existing file. Stop and report conflicts for semantic merge or explicit user choice. Merge portable agent rules into the target's user-level rules; do not replace the entire target rule file. Reinstall managed Skills from their recorded sources, then verify their versions and triggers.

After file restoration:

1. Install or present this Skill to the target agent.
2. Run a full canonical read, rebuild and verify the lifecycle index, then load the relevant domain package.
3. Run the one-time Agent onboarding workflow and record its actual status.
4. Summarize what was recovered and what remains unavailable.
5. Complete one small reversible task.
6. Trigger a durable-memory update and verify Obsidian-first/local-second ordering.
7. Complete a no-change conversation and verify neither store gains fabricated entries.
8. Confirm routine memory maintenance did not run Git or remote sync.

## Work with non-Codex agents

If the target supports Agent Skills, install the folder in its documented user Skill location. Otherwise give the agent `SKILL.md`, `HANDOFF.md`, `PORTABLE_MEMORY_POLICY.md`, and the restored vault path as an explicit operating protocol. Adapt only the installation, rule-file location, and documented native-memory adapter; do not weaken authority, evidence, privacy, conflict, or audit rules.

Do not pretend unsupported tools exist. Produce a manual merge plan when the target cannot execute the bundled Python script or cannot persist files.

## Privacy gate

Never store or export passwords, tokens, cookies, API keys, private keys, authentication files, browser data, account databases, full chats, unrelated personal data, sensitive terminal dumps, or hidden chain-of-thought. Do not infer personality, motives, health, finances, relationships, or ability from a single interaction. Preserve an impression only when it affects future work, has concrete evidence, is revisable, and is not a sensitive inference.

## Completion criteria

Declare routine canonical memory maintenance complete when required Obsidian files are updated and readable, the index has been atomically rebuilt, source fingerprints match, and health has no blocking error. Declare dual-memory maintenance complete only when the verified local mirror also confirms the same changed IDs; otherwise state the exact degraded status. An installed rule block is not proof of automatic loading, and a readable file is not proof that the product consumes it. Declare onboarding complete only when `rules_autoload`, native-memory verification when applicable, and `acceptance_status` have evidence. Declare an export complete only when its manifest and checksums verify. Declare restoration complete only when the memory package, lifecycle health, dual-memory policy, Agent registry, required context, portable rules, user-owned Skills, managed-Skill reinstall plan, conflict report, onboarding status, and a fresh-context handoff check all pass. List every unavailable category instead of calling a partial restore complete.
