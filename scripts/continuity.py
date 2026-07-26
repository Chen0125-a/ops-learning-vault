#!/usr/bin/env python3
"""Portable, fail-closed continuity bundle tooling.

The module uses only the Python standard library so a fresh agent can audit,
export, verify, and restore explicit user-owned context without copying account
state, caches, or credentials.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


MEMORY_DIR_NAME = "AI协作-通用记忆包"
PORTABILITY_MANIFEST = "PORTABILITY_MANIFEST.json"
AGENT_MEMORY_REGISTRY = "AGENT_MEMORY_REGISTRY.json"
PORTABLE_MEMORY_POLICY = "PORTABLE_MEMORY_POLICY.md"
POLICY_BEGIN = "<!-- OBSIDIAN-CONTINUITY:BEGIN -->"
POLICY_END = "<!-- OBSIDIAN-CONTINUITY:END -->"
CORE_MEMORY_FILES = (
    "README.md",
    "CURRENT.md",
    "USER_PROFILE.md",
    "COLLABORATION_MEMORY.md",
    "DECISIONS.md",
    "LESSONS.md",
    "ENVIRONMENT.md",
    "MEMORY_INBOX.md",
    "MEMORY_CHANGELOG.md",
    "RESTORE.md",
    "BACKUP.md",
    PORTABLE_MEMORY_POLICY,
    AGENT_MEMORY_REGISTRY,
)
SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".obsidian",
    ".system",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "cache",
    "caches",
}
FORBIDDEN_NAME_PATTERNS = (
    re.compile(r"(?i)^\.env(?:\..*)?$"),
    re.compile(r"(?i)^auth\.json$"),
    re.compile(r"(?i)(?:^|[._-])(token|secret|credential|cookies?)(?:[._-]|$)"),
    re.compile(r"(?i)\.(pem|key|pfx|p12|kdbx|sqlite|sqlite3)$"),
)
HIGH_CONFIDENCE_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
)
LABEL_RE = re.compile(r"^[A-Za-z0-9._-]+$")
MANAGED_SOURCE_TYPES = {"repository", "catalog", "plugin", "package", "local-inventory"}
DUAL_MEMORY_STATUSES = {
    "verified",
    "degraded-no-native-memory-file",
    "degraded-unverified-native-memory-path",
    "degraded-unverified-native-memory-adapter",
    "degraded-unverified-rules-autoload",
}
NATIVE_MEMORY_MODES = {"file-mirror", "api-adapter", "unavailable-or-unverified"}

PORTABLE_RULE_BLOCK = """{begin}
## Portable collaboration continuity

- Treat the Obsidian `AI协作-通用记忆包` as the canonical, cross-agent memory ledger. Treat any agent-native memory as a local mirror/cache, never as an equal authority.
- At the start of work that needs durable user context, invoke `obsidian-user-memory`, discover the vault, read the six core memory files in their required order, and reconcile accessible local memory against them.
- Before every final reply, audit only durable deltas. Write validated changes to Obsidian first, append `MEMORY_CHANGELOG.md`, then mirror a compact summary with stable IDs through a verified native-memory file or API adapter.
- Resolve conflicts by this order: current primary evidence or explicit user correction; validated Obsidian entry; agent-local memory; unverified candidate. Never silently overwrite unresolved conflicts.
- Never store passwords, tokens, cookies, private keys, authentication files, full chats, hidden reasoning, or irrelevant private data. Routine memory updates never perform Git commit or push.
- If no documented writable native-memory mechanism is available, continue from Obsidian and report `degraded-no-native-memory-file`; never claim that dual-memory sync succeeded.
{end}""".format(begin=POLICY_BEGIN, end=POLICY_END)


class ContinuityError(RuntimeError):
    pass


class ValidationError(ContinuityError):
    pass


class SecurityError(ContinuityError):
    pass


def _is_memory_package(path):
    path = Path(path)
    return all((path / name).is_file() for name in ("README.md", "CURRENT.md", "COLLABORATION_MEMORY.md"))


def _package_below(path):
    path = Path(path).expanduser()
    if _is_memory_package(path):
        return path.resolve()
    named = path / MEMORY_DIR_NAME
    if _is_memory_package(named):
        return named.resolve()
    if path.is_dir():
        for child in sorted(path.iterdir(), key=lambda item: item.name):
            if child.is_dir() and _is_memory_package(child):
                return child.resolve()
    return None


def discover_memory_package(explicit=None, start=None):
    """Locate the package without recursively crawling an entire disk."""
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    for variable in ("OBSIDIAN_MEMORY_VAULT", "OBSIDIAN_VAULT"):
        if os.environ.get(variable):
            candidates.append(Path(os.environ[variable]))

    origin = Path(start or Path.cwd()).expanduser().resolve()
    candidates.extend([origin] + list(origin.parents))
    candidates.extend(
        [
            Path.home() / "Documents" / "Obsidian",
            Path.home() / "Obsidian",
        ]
    )
    if os.name == "nt":
        candidates.append(Path("D:/笔记"))

    seen = set()
    for candidate in candidates:
        key = str(candidate).casefold()
        if key in seen:
            continue
        seen.add(key)
        found = _package_below(candidate)
        if found:
            return found
    raise FileNotFoundError(
        "Portable memory package not found. Supply --vault or set OBSIDIAN_MEMORY_VAULT."
    )


def _vault_and_package(vault_or_package):
    package = discover_memory_package(explicit=vault_or_package)
    return package.parent, package


def _load_manifest(package):
    path = Path(package) / PORTABILITY_MANIFEST
    if not path.is_file():
        raise ValidationError("Missing portability manifest: {}".format(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("Invalid portability manifest: {}".format(exc)) from exc
    if data.get("schema_version") != 3:
        raise ValidationError("Unsupported schema_version; expected 3")
    if data.get("memory_package") != Path(package).name:
        raise ValidationError("Manifest memory_package does not match the package directory")
    if not isinstance(data.get("context_paths"), list):
        raise ValidationError("Manifest context_paths must be a list")
    if not isinstance(data.get("required_skills"), list):
        raise ValidationError("Manifest required_skills must be a list")
    protocol = data.get("memory_protocol")
    if not isinstance(protocol, dict):
        raise ValidationError("Manifest memory_protocol must be an object")
    expected_protocol = {
        "canonical_store": "obsidian",
        "policy": "{}/{}".format(Path(package).name, PORTABLE_MEMORY_POLICY),
        "agent_registry": "{}/{}".format(Path(package).name, AGENT_MEMORY_REGISTRY),
        "sync_order": ["pull-before-work", "push-before-final-reply"],
    }
    for field, expected in expected_protocol.items():
        if protocol.get(field) != expected:
            raise ValidationError(
                "Manifest memory_protocol.{} must equal {}".format(
                    field, json.dumps(expected, ensure_ascii=False)
                )
            )
    return data


def _load_agent_registry(package):
    path = Path(package) / AGENT_MEMORY_REGISTRY
    if not path.is_file():
        raise ValidationError("Missing agent memory registry: {}".format(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("Invalid {}: {}".format(AGENT_MEMORY_REGISTRY, exc)) from exc
    errors = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("canonical_store") != "obsidian":
        errors.append("canonical_store must be obsidian")
    agents = data.get("agents")
    if not isinstance(agents, list):
        errors.append("agents must be a list")
        agents = []
    seen = set()
    required = (
        "agent_id",
        "product",
        "rules_file",
        "rules_autoload",
        "rules_autoload_evidence",
        "native_memory_paths",
        "native_memory_mode",
        "native_memory_status",
        "native_memory_verification",
        "dual_memory_status",
        "acceptance_status",
        "sync_trigger",
        "last_verified",
    )
    for index, item in enumerate(agents):
        label = "agents[{}]".format(index)
        if not isinstance(item, dict):
            errors.append("{} must be an object".format(label))
            continue
        missing = [field for field in required if field not in item]
        if missing:
            errors.append("{} missing fields: {}".format(label, ", ".join(missing)))
            continue
        agent_id = item["agent_id"]
        if not isinstance(agent_id, str) or not LABEL_RE.match(agent_id):
            errors.append("{}.agent_id must match {}".format(label, LABEL_RE.pattern))
        elif agent_id in seen:
            errors.append("duplicate agent_id: {}".format(agent_id))
        seen.add(agent_id)
        if not isinstance(item["product"], str) or not item["product"].strip():
            errors.append("{}.product must be a non-empty string".format(label))
        if not isinstance(item["rules_file"], str) or not item["rules_file"].strip():
            errors.append("{}.rules_file must be a non-empty string".format(label))
        if item["rules_autoload"] not in {"verified", "pending-fresh-task-verification"}:
            errors.append("{}.rules_autoload is unsupported".format(label))
        if not isinstance(item["rules_autoload_evidence"], str) or not item[
            "rules_autoload_evidence"
        ].strip():
            errors.append("{}.rules_autoload_evidence must be a non-empty string".format(label))
        if not isinstance(item["native_memory_paths"], list) or not all(
            isinstance(value, str) and value for value in item["native_memory_paths"]
        ):
            errors.append("{}.native_memory_paths must be a list of paths".format(label))
        if item["native_memory_mode"] not in NATIVE_MEMORY_MODES:
            errors.append("{}.native_memory_mode is unsupported".format(label))
        if item["native_memory_status"] not in DUAL_MEMORY_STATUSES - {
            "degraded-unverified-rules-autoload"
        }:
            errors.append("{}.native_memory_status is unsupported".format(label))
        verification = item["native_memory_verification"]
        if not isinstance(verification, dict) or not all(
            isinstance(verification.get(field), str) and verification.get(field)
            for field in ("status", "method", "evidence")
        ):
            errors.append(
                "{}.native_memory_verification requires status, method, and evidence".format(label)
            )
        if item["dual_memory_status"] not in DUAL_MEMORY_STATUSES:
            errors.append("{}.dual_memory_status is unsupported".format(label))
        if (
            item["dual_memory_status"] == "verified"
            and item["native_memory_mode"] == "file-mirror"
            and not item["native_memory_paths"]
        ):
            errors.append("{} verified file-mirror requires native_memory_paths".format(label))
        if (
            item["dual_memory_status"] == "verified"
            and item["native_memory_mode"] == "api-adapter"
            and not item.get("native_memory_adapter")
        ):
            errors.append("{} verified api-adapter requires native_memory_adapter".format(label))
        if item["sync_trigger"] != "before-final-reply":
            errors.append("{}.sync_trigger must be before-final-reply".format(label))
        if item["acceptance_status"] not in {"verified", "pending-fresh-task-drill"}:
            errors.append("{}.acceptance_status is unsupported".format(label))
    if errors:
        raise ValidationError("Invalid {}: {}".format(AGENT_MEMORY_REGISTRY, "; ".join(errors)))
    return data


def _is_within(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def _context_source(vault_root, relative):
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValidationError("Context path must be relative and stay inside the vault: {}".format(relative))
    source = (Path(vault_root) / relative_path).resolve()
    if not _is_within(source, vault_root):
        raise ValidationError("Context path escapes the vault: {}".format(relative))
    return source


def _iter_files(source):
    source = Path(source)
    if source.is_symlink():
        yield source
        return
    if source.is_file():
        yield source
        return
    if not source.is_dir():
        return
    for root, dirs, files in os.walk(str(source), followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIR_NAMES)
        for name in sorted(files):
            yield Path(root) / name


def _looks_text(path):
    try:
        sample = Path(path).read_bytes()[:4096]
    except OSError:
        return False
    return b"\x00" not in sample


def scan_for_secrets(paths):
    findings = []
    seen = set()
    for source in paths:
        for path in _iter_files(source):
            resolved = str(path.resolve()) if path.exists() else str(path)
            if resolved in seen:
                continue
            seen.add(resolved)
            if path.is_symlink():
                findings.append({"kind": "symlink", "path": str(path)})
                continue
            for pattern in FORBIDDEN_NAME_PATTERNS:
                if pattern.search(path.name):
                    findings.append({"kind": "forbidden-name", "path": str(path)})
                    break
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > 2 * 1024 * 1024 or not _looks_text(path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for pattern in HIGH_CONFIDENCE_SECRET_PATTERNS:
                if pattern.search(text):
                    findings.append({"kind": "high-confidence-secret", "path": str(path)})
                    break
    return findings


def _skill_index(skill_roots):
    found = {}
    for root in skill_roots or []:
        root = Path(root).expanduser()
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if child.is_dir() and not child.name.startswith(".") and (child / "SKILL.md").is_file():
                found.setdefault(child.name, child.resolve())
    return found


def _validate_managed_skill_sets(manifest):
    errors = []
    required = set()
    seen_names = set()
    sets = manifest.get("managed_skill_sets")
    if not isinstance(sets, list):
        return ["Manifest managed_skill_sets must be a list"], required
    required_fields = ("name", "source_type", "source", "restore", "required", "inventory")
    for index, item in enumerate(sets):
        label = "managed_skill_sets[{}]".format(index)
        if not isinstance(item, dict):
            errors.append("{} must be an object".format(label))
            continue
        missing = [field for field in required_fields if field not in item]
        if missing:
            errors.append("{} missing fields: {}".format(label, ", ".join(missing)))
            continue
        if item["source_type"] not in MANAGED_SOURCE_TYPES:
            errors.append(
                "{} source_type must be one of: {}".format(
                    label, ", ".join(sorted(MANAGED_SOURCE_TYPES))
                )
            )
        if not isinstance(item["source"], str) or not item["source"].strip():
            errors.append("{} source must be a non-empty string".format(label))
        if not isinstance(item["restore"], str) or not item["restore"].strip():
            errors.append("{} restore must be a non-empty string".format(label))
        if not isinstance(item["required"], bool):
            errors.append("{} required must be a boolean".format(label))
        inventory = item["inventory"]
        if not isinstance(inventory, list) or not all(isinstance(name, str) and name for name in inventory):
            errors.append("{} inventory must be a list of non-empty Skill names".format(label))
            continue
        duplicates = sorted(seen_names.intersection(inventory))
        if duplicates:
            errors.append("{} duplicates managed Skills: {}".format(label, ", ".join(duplicates)))
        seen_names.update(inventory)
        if item["source_type"] == "local-inventory" and not item.get("bundle_group"):
            errors.append("{} local-inventory requires bundle_group".format(label))
        if item["required"]:
            required.update(inventory)
    return errors, required


def verify_package(vault_or_package, skill_roots=None):
    vault_root, package = _vault_and_package(vault_or_package)
    missing_files = [
        name for name in CORE_MEMORY_FILES + (PORTABILITY_MANIFEST,) if not (package / name).is_file()
    ]
    errors = []
    missing_context = []
    missing_skills = []
    missing_managed_skills = []
    security_sources = [package]
    manifest = None
    try:
        manifest = _load_manifest(package)
    except ValidationError as exc:
        errors.append(str(exc))
    if (package / AGENT_MEMORY_REGISTRY).is_file():
        try:
            _load_agent_registry(package)
        except ValidationError as exc:
            errors.append(str(exc))

    if manifest:
        for item in manifest["context_paths"]:
            if not isinstance(item, dict) or not item.get("path"):
                errors.append("Every context_paths item must contain path")
                continue
            try:
                source = _context_source(vault_root, item["path"])
            except ValidationError as exc:
                errors.append(str(exc))
                continue
            if item.get("required", False) and not source.exists():
                missing_context.append(item["path"])
            if source.exists():
                security_sources.append(source)
        available = _skill_index(skill_roots)
        managed_errors, required_managed = _validate_managed_skill_sets(manifest)
        errors.extend(managed_errors)
        if skill_roots is not None:
            missing_skills = sorted(set(manifest["required_skills"]) - set(available))
            missing_managed_skills = sorted(required_managed - set(available))
            security_sources.extend(
                available[name] for name in manifest["required_skills"] if name in available
            )
            security_sources.extend(available[name] for name in required_managed if name in available)

    secret_findings = scan_for_secrets(security_sources) if package.is_dir() else []
    ok = not (
        missing_files
        or errors
        or missing_context
        or missing_skills
        or missing_managed_skills
        or secret_findings
    )
    return {
        "ok": ok,
        "package": str(package),
        "vault_root": str(vault_root),
        "missing_files": missing_files,
        "missing_context": missing_context,
        "missing_skills": missing_skills,
        "missing_managed_skills": missing_managed_skills,
        "errors": errors,
        "security_findings": secret_findings,
    }


def _copy_source(source, destination):
    source = Path(source)
    destination = Path(destination)
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(destination))
        return
    for file_path in _iter_files(source):
        relative = file_path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(file_path), str(target))


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_checksums(bundle):
    bundle = Path(bundle)
    entries = []
    for path in sorted(_iter_files(bundle), key=lambda item: item.as_posix()):
        relative = path.relative_to(bundle).as_posix()
        if relative == "checksums.sha256":
            continue
        entries.append("{}  {}".format(_sha256(path), relative))
    (bundle / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")
    return len(entries)


def _handoff_text():
    return """# Portable Agent Handoff

This bundle contains explicit, user-owned continuity data. It does not contain model internals,
account sessions, credentials, cookies, or hidden reasoning.

1. Verify `checksums.sha256` before trusting any file.
2. Read `vault/AI协作-通用记忆包/PORTABLE_MEMORY_POLICY.md`,
   `AGENT_MEMORY_REGISTRY.json`, and `PORTABILITY_MANIFEST.json`.
3. Read the six core memory files in the order required by the bundled Skill.
4. Load domain context only when its activation condition applies.
5. Install or present `skills/*/*/SKILL.md` to the new agent; merge rules semantically and never
   overwrite unrelated local rules.
6. Discover the new agent's documented persistent-rule and native-memory interfaces. Preview
   `bootstrap-agent` before applying it; never invent a `MEMORY.md` path.
7. Run a read-only restoration check before making changes. Preserve conflicts for user review.
8. Pull Obsidian context before work. Before the final reply, write durable deltas to Obsidian
   first and then to a verified local-memory mirror using the same stable IDs.
9. Report degraded local-memory status honestly and never run Git during routine memory sync.
"""


def export_bundle(vault_root, output, skill_roots):
    vault_root, package = _vault_and_package(vault_root)
    manifest = _load_manifest(package)
    output = Path(output).expanduser()
    if output.exists():
        raise ValidationError("Output must not already exist: {}".format(output))

    skill_roots = skill_roots or {}
    for label in skill_roots:
        if not LABEL_RE.match(label):
            raise ValidationError("Invalid skill-root label: {}".format(label))

    package_report = verify_package(vault_root, skill_roots=list(skill_roots.values()))
    if package_report["security_findings"]:
        raise SecurityError(
            "Export blocked by security findings: {}".format(
                json.dumps(package_report["security_findings"], ensure_ascii=False)
            )
        )
    if not package_report["ok"]:
        raise ValidationError("Package verification failed: {}".format(json.dumps(package_report, ensure_ascii=False)))

    context_sources = []
    for item in manifest["context_paths"]:
        source = _context_source(vault_root, item["path"])
        if source.exists():
            context_sources.append((item["path"], source))

    skill_sources = []
    for label, root_value in sorted(skill_roots.items()):
        root = Path(root_value).expanduser().resolve()
        if not root.is_dir():
            raise ValidationError("Skill root does not exist: {}".format(root))
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if child.name.startswith(".") or not child.is_dir() or not (child / "SKILL.md").is_file():
                continue
            skill_sources.append((label, child.name, child))

    findings = scan_for_secrets(
        [source for _, source in context_sources] + [source for _, _, source in skill_sources]
    )
    if findings:
        raise SecurityError("Export blocked by security findings: {}".format(json.dumps(findings, ensure_ascii=False)))

    temporary = output.with_name(output.name + ".partial-" + uuid.uuid4().hex[:8])
    try:
        temporary.mkdir(parents=True)
        for relative, source in context_sources:
            _copy_source(source, temporary / "vault" / Path(relative))
        for label, name, source in skill_sources:
            _copy_source(source, temporary / "skills" / label / name)

        bundle_manifest = {
            "schema_version": 1,
            "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "memory_package": manifest["memory_package"],
            "context_paths": [item[0] for item in context_sources],
            "skill_groups": {
                label: sorted(name for group, name, _ in skill_sources if group == label)
                for label in sorted(skill_roots)
            },
            "excluded": sorted(SKIP_DIR_NAMES),
            "restore_policy": "dry-run-first; never overwrite conflicts",
        }
        (temporary / "bundle-manifest.json").write_text(
            json.dumps(bundle_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (temporary / "HANDOFF.md").write_text(_handoff_text(), encoding="utf-8")
        file_count = _write_checksums(temporary)
        temporary.replace(output)
    except Exception:
        if temporary.exists():
            shutil.rmtree(str(temporary))
        raise

    return {
        "ok": True,
        "bundle": str(output.resolve()),
        "files": file_count,
        "skills": len(skill_sources),
        "contexts": len(context_sources),
    }


def _parse_checksums(bundle):
    checksum_file = Path(bundle) / "checksums.sha256"
    if not checksum_file.is_file():
        raise ValidationError("Missing checksums.sha256")
    entries = {}
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        match = re.match(r"^([0-9a-f]{64})  (.+)$", line)
        if not match:
            raise ValidationError("Malformed checksum line: {}".format(line))
        relative = Path(match.group(2))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValidationError("Unsafe checksum path: {}".format(relative))
        entries[relative.as_posix()] = match.group(1)
    return entries


def verify_bundle(bundle):
    bundle = Path(bundle).expanduser().resolve()
    try:
        expected = _parse_checksums(bundle)
    except ValidationError as exc:
        return {"ok": False, "missing": [], "mismatched": [], "unexpected": [], "errors": [str(exc)]}
    actual = {
        path.relative_to(bundle).as_posix()
        for path in _iter_files(bundle)
        if path.relative_to(bundle).as_posix() != "checksums.sha256"
    }
    missing = sorted(set(expected) - actual)
    unexpected = sorted(actual - set(expected))
    mismatched = []
    for relative, expected_hash in expected.items():
        path = bundle / Path(relative)
        if path.is_file() and _sha256(path) != expected_hash:
            mismatched.append(relative)
    return {
        "ok": not (missing or mismatched or unexpected),
        "missing": missing,
        "mismatched": sorted(mismatched),
        "unexpected": unexpected,
        "errors": [],
    }


def _target_is_safe(target, bundle):
    target = Path(target).expanduser().resolve()
    bundle = Path(bundle).resolve()
    return not (_is_within(target, bundle) or _is_within(bundle, target))


def restore_bundle(bundle, target_vault, skill_targets, apply=False):
    bundle = Path(bundle).expanduser().resolve()
    verification = verify_bundle(bundle)
    if not verification["ok"]:
        return {"ok": False, "conflicts": [], "errors": ["Bundle integrity verification failed"], "verification": verification}

    target_vault = Path(target_vault).expanduser().resolve()
    if not _target_is_safe(target_vault, bundle):
        raise ValidationError("Target vault must not contain or be contained by the bundle")
    skill_targets = skill_targets or {}
    operations = []
    errors = []

    vault_source = bundle / "vault"
    for source in _iter_files(vault_source):
        relative = source.relative_to(vault_source)
        operations.append(("vault/" + relative.as_posix(), source, target_vault / relative))

    skills_source = bundle / "skills"
    if skills_source.is_dir():
        for group in sorted(path for path in skills_source.iterdir() if path.is_dir()):
            target_root = skill_targets.get(group.name)
            if target_root is None:
                errors.append("Missing restore target for skill group: {}".format(group.name))
                continue
            target_root = Path(target_root).expanduser().resolve()
            if not _target_is_safe(target_root, bundle):
                raise ValidationError("Skill target must not contain or be contained by the bundle")
            for source in _iter_files(group):
                relative = source.relative_to(group)
                operations.append(
                    ("skills/{}/{}".format(group.name, relative.as_posix()), source, target_root / relative)
                )

    conflicts = []
    pending = []
    identical = []
    for logical, source, target in operations:
        if target.exists():
            if target.is_file() and _sha256(source) == _sha256(target):
                identical.append(logical)
            else:
                conflicts.append(logical)
        else:
            pending.append((logical, source, target))

    if conflicts or errors:
        return {
            "ok": False,
            "apply": bool(apply),
            "planned": len(pending),
            "identical": len(identical),
            "conflicts": sorted(conflicts),
            "errors": errors,
        }

    if apply:
        for _, source, target in pending:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source), str(target))
    return {
        "ok": True,
        "apply": bool(apply),
        "planned": len(pending),
        "written": len(pending) if apply else 0,
        "identical": len(identical),
        "conflicts": [],
        "errors": [],
    }


def _portable_path(path):
    resolved = Path(path).expanduser().resolve()
    home = Path.home().resolve()
    try:
        relative = resolved.relative_to(home)
        return "~/{}".format(relative.as_posix())
    except ValueError:
        return resolved.as_posix()


def _atomic_write_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex[:8])
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def _merge_portable_rule_block(existing):
    begin_count = existing.count(POLICY_BEGIN)
    end_count = existing.count(POLICY_END)
    if begin_count == 0 and end_count == 0:
        prefix = existing.rstrip()
        merged = (prefix + "\n\n" if prefix else "") + PORTABLE_RULE_BLOCK + "\n"
        return "append", merged
    if begin_count != 1 or end_count != 1:
        return "conflict", existing
    begin = existing.index(POLICY_BEGIN)
    end = existing.index(POLICY_END, begin) + len(POLICY_END)
    if existing[begin:end] != PORTABLE_RULE_BLOCK:
        return "conflict", existing
    return "identical", existing


def _native_memory_status(paths, adapter=None, roundtrip_verified=False):
    if paths and adapter:
        raise ValidationError("Use native memory files or an API adapter, not both")
    if adapter:
        return "verified" if roundtrip_verified else "degraded-unverified-native-memory-adapter"
    if not paths:
        return "degraded-no-native-memory-file"
    usable = all(
        path.is_file() and os.access(str(path), os.R_OK) and os.access(str(path), os.W_OK)
        for path in paths
    )
    return "verified" if usable and roundtrip_verified else "degraded-unverified-native-memory-path"


def bootstrap_agent(
    vault_or_package,
    agent_id,
    product,
    rules_file,
    native_memory_paths=None,
    native_memory_adapter=None,
    rules_autoload_verified=False,
    native_memory_verified=False,
    acceptance_drill_verified=False,
    apply=False,
):
    """Preview or install the portable policy into one agent's persistent rules.

    The caller must first verify that ``rules_file`` is documented and automatically
    loaded by the target agent. Native memory paths are registered only when they are
    explicit files. A file or API adapter reaches ``verified`` only after the caller
    confirms a real round trip; this function never invents or initializes a platform memory store.
    """
    if not isinstance(agent_id, str) or not LABEL_RE.match(agent_id):
        raise ValidationError("agent_id must match {}".format(LABEL_RE.pattern))
    if not isinstance(product, str) or not product.strip():
        raise ValidationError("product must be a non-empty string")
    _, package = _vault_and_package(vault_or_package)
    _load_manifest(package)
    registry = _load_agent_registry(package)

    rules_path = Path(rules_file).expanduser().resolve()
    if rules_path.exists() and not rules_path.is_file():
        raise ValidationError("rules_file must be a file or a new file path: {}".format(rules_path))
    try:
        existing = rules_path.read_text(encoding="utf-8") if rules_path.is_file() else ""
    except (OSError, UnicodeDecodeError) as exc:
        raise ValidationError("Cannot read rules_file as UTF-8: {}".format(exc)) from exc
    rule_status, merged = _merge_portable_rule_block(existing)
    if rule_status == "conflict":
        return {
            "ok": False,
            "apply": bool(apply),
            "status": "conflict",
            "rules_file": str(rules_path),
            "dual_memory_status": None,
            "errors": ["Existing Obsidian continuity block differs; semantic review required"],
        }

    native_paths = [Path(value).expanduser().resolve() for value in (native_memory_paths or [])]
    if native_memory_adapter is not None:
        if not isinstance(native_memory_adapter, str) or not native_memory_adapter.strip():
            raise ValidationError("native_memory_adapter must be a non-empty non-secret reference")
        native_memory_adapter = native_memory_adapter.strip()
    existing_entry = next(
        (item for item in registry["agents"] if item.get("agent_id") == agent_id),
        {},
    )
    portable_rules_path = _portable_path(rules_path)
    portable_native_paths = [_portable_path(path) for path in native_paths]
    same_rules = existing_entry.get("rules_file") == portable_rules_path
    same_native = (
        existing_entry.get("native_memory_paths", []) == portable_native_paths
        and existing_entry.get("native_memory_adapter") == native_memory_adapter
    )
    effective_rules_verified = bool(rules_autoload_verified) or (
        same_rules and existing_entry.get("rules_autoload") == "verified"
    )
    effective_native_verified = bool(native_memory_verified) or (
        same_native and existing_entry.get("native_memory_status") == "verified"
    )
    effective_acceptance_verified = bool(acceptance_drill_verified) or (
        same_rules and same_native and existing_entry.get("acceptance_status") == "verified"
    )
    if native_memory_verified and not (native_memory_adapter or native_paths):
        raise ValidationError(
            "native_memory_verified requires native memory files or an API adapter"
        )
    native_status = _native_memory_status(
        native_paths,
        adapter=native_memory_adapter,
        roundtrip_verified=effective_native_verified,
    )
    if acceptance_drill_verified and not effective_rules_verified:
        raise ValidationError("acceptance_drill_verified requires verified rule autoload")
    if acceptance_drill_verified and (native_paths or native_memory_adapter) and native_status != "verified":
        raise ValidationError("acceptance_drill_verified requires verified native memory")
    memory_status = (
        "degraded-unverified-rules-autoload"
        if native_status == "verified" and not effective_rules_verified
        else native_status
    )
    entry = dict(existing_entry)
    entry.update({
        "agent_id": agent_id,
        "product": product.strip(),
        "rules_file": portable_rules_path,
        "rules_autoload": (
            "verified" if effective_rules_verified else "pending-fresh-task-verification"
        ),
        "rules_autoload_evidence": (
            "Caller confirmed automatic loading in a fresh task"
            if effective_rules_verified
            else "Policy block installed or previewed; fresh-task autoload not yet confirmed"
        ),
        "native_memory_paths": portable_native_paths,
        "native_memory_mode": (
            "api-adapter"
            if native_memory_adapter
            else "file-mirror"
            if native_paths
            else "unavailable-or-unverified"
        ),
        "native_memory_status": native_status,
        "native_memory_verification": {
            "status": (
                "verified"
                if native_status == "verified"
                else "unavailable"
                if native_status == "degraded-no-native-memory-file"
                else "pending"
            ),
            "method": (
                "create-read-update-roundtrip"
                if effective_native_verified
                else "not-applicable"
                if native_status == "degraded-no-native-memory-file"
                else "roundtrip-not-confirmed"
            ),
            "evidence": (
                "Caller confirmed a real round trip through the documented product interface"
                if effective_native_verified
                else "No verified round trip was supplied"
            ),
        },
        "dual_memory_status": memory_status,
        "acceptance_status": (
            "verified" if effective_acceptance_verified else "pending-fresh-task-drill"
        ),
        "sync_trigger": "before-final-reply",
        "last_verified": datetime.now(timezone.utc).date().isoformat(),
    })
    if native_memory_adapter:
        entry["native_memory_adapter"] = native_memory_adapter
    else:
        entry.pop("native_memory_adapter", None)
    agents = [item for item in registry["agents"] if item.get("agent_id") != agent_id]
    agents.append(entry)
    agents.sort(key=lambda item: item["agent_id"])
    updated_registry = dict(registry)
    updated_registry["agents"] = agents
    registry_text = json.dumps(updated_registry, ensure_ascii=False, indent=2) + "\n"

    if apply:
        if rule_status == "append":
            _atomic_write_text(rules_path, merged)
        _atomic_write_text(package / AGENT_MEMORY_REGISTRY, registry_text)

    return {
        "ok": True,
        "apply": bool(apply),
        "status": "installed" if apply and rule_status == "append" else rule_status,
        "rules_file": str(rules_path),
        "registry": str(package / AGENT_MEMORY_REGISTRY),
        "dual_memory_status": memory_status,
        "native_memory_status": native_status,
        "rules_autoload": entry["rules_autoload"],
        "acceptance_status": entry["acceptance_status"],
        "native_memory_paths": [str(path) for path in native_paths],
        "native_memory_adapter": native_memory_adapter,
        "warnings": (
            []
            if memory_status == "verified"
            else ["No verified native memory adapter; Obsidian-only continuity remains active"]
        ),
    }


def _parse_mapping(values, option):
    result = {}
    for value in values or []:
        if "=" not in value:
            raise ValidationError("{} requires LABEL=PATH: {}".format(option, value))
        label, path = value.split("=", 1)
        if not LABEL_RE.match(label) or not path:
            raise ValidationError("Invalid {} value: {}".format(option, value))
        result[label] = Path(path)
    return result


def _print_report(report):
    print(json.dumps(report, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Portable agent continuity tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    discover = sub.add_parser("discover", help="Locate the Obsidian memory package")
    discover.add_argument("--vault")
    discover.add_argument("--start")

    verify = sub.add_parser("verify", help="Verify memory, manifest, and expected skills")
    verify.add_argument("--vault", required=True)
    verify.add_argument("--skill-root", action="append", default=[])

    export = sub.add_parser("export", help="Create a checked portable bundle")
    export.add_argument("--vault", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--skill-root", action="append", default=[], metavar="LABEL=PATH")

    bundle = sub.add_parser("verify-bundle", help="Verify bundle checksums")
    bundle.add_argument("--bundle", required=True)

    restore = sub.add_parser("restore", help="Preview or apply a non-overwriting restore")
    restore.add_argument("--bundle", required=True)
    restore.add_argument("--target-vault", required=True)
    restore.add_argument("--skill-target", action="append", default=[], metavar="LABEL=PATH")
    restore.add_argument("--apply", action="store_true")

    bootstrap = sub.add_parser(
        "bootstrap-agent",
        help="Preview or install the continuity policy in one agent's persistent rules",
    )
    bootstrap.add_argument("--vault", required=True)
    bootstrap.add_argument("--agent-id", required=True)
    bootstrap.add_argument("--product", required=True)
    bootstrap.add_argument("--rules-file", required=True)
    bootstrap.add_argument("--native-memory", action="append", default=[])
    bootstrap.add_argument("--native-memory-adapter")
    bootstrap.add_argument("--confirm-rules-autoload", action="store_true")
    bootstrap.add_argument("--confirm-native-memory-roundtrip", action="store_true")
    bootstrap.add_argument("--confirm-acceptance-drill", action="store_true")
    bootstrap.add_argument("--apply", action="store_true")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "discover":
            print(discover_memory_package(args.vault, args.start))
            return 0
        if args.command == "verify":
            report = verify_package(args.vault, [Path(item) for item in args.skill_root])
        elif args.command == "export":
            report = export_bundle(args.vault, args.output, _parse_mapping(args.skill_root, "--skill-root"))
        elif args.command == "verify-bundle":
            report = verify_bundle(args.bundle)
        elif args.command == "restore":
            report = restore_bundle(
                args.bundle,
                args.target_vault,
                _parse_mapping(args.skill_target, "--skill-target"),
                apply=args.apply,
            )
        else:
            report = bootstrap_agent(
                args.vault,
                args.agent_id,
                args.product,
                args.rules_file,
                native_memory_paths=args.native_memory,
                native_memory_adapter=args.native_memory_adapter,
                rules_autoload_verified=args.confirm_rules_autoload,
                native_memory_verified=args.confirm_native_memory_roundtrip,
                acceptance_drill_verified=args.confirm_acceptance_drill,
                apply=args.apply,
            )
        _print_report(report)
        return 0 if report.get("ok") else 1
    except (ContinuityError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
