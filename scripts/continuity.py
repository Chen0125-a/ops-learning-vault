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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


MEMORY_DIR_NAME = "AI协作-通用记忆包"
PORTABILITY_MANIFEST = "PORTABILITY_MANIFEST.json"
AGENT_MEMORY_REGISTRY = "AGENT_MEMORY_REGISTRY.json"
PORTABLE_MEMORY_POLICY = "PORTABLE_MEMORY_POLICY.md"
MEMORY_INDEX = "MEMORY_INDEX.json"
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
INDEX_SOURCE_FILES = (
    "CURRENT.md",
    "USER_PROFILE.md",
    "COLLABORATION_MEMORY.md",
    "DECISIONS.md",
    "LESSONS.md",
    "ENVIRONMENT.md",
    "MEMORY_INBOX.md",
)
ENTRY_SOURCE_FILES = INDEX_SOURCE_FILES[1:]
ENTRY_HEADING_RE = re.compile(
    r"(?m)^#{2,4}\s+([A-Z]{1,4}-\d{3,}|MI-\d{8}-\d{3})[：:]\s*(.+?)\s*$"
)
FRONTMATTER_REVIEWED_RE = re.compile(r"(?m)^reviewed:\s*(\d{4}-\d{2}-\d{2})\s*$")
VALID_ENTRY_STATUSES = {"active", "candidate", "review-due", "superseded", "archived"}
VALID_MEMORY_TIERS = {"hot", "warm", "cold", "archive"}
DEFAULT_HOT_BUDGET_CHARS = 12000
CURRENT_STALE_DAYS = 14

PORTABLE_RULE_BLOCK = """{begin}
## Portable collaboration continuity

- Treat the Obsidian `AI协作-通用记忆包` as the canonical, cross-agent memory ledger. Treat any agent-native memory as a local mirror/cache, never as an equal authority.
- At the start of ordinary work that needs durable user context, invoke `obsidian-user-memory`, verify `MEMORY_INDEX.json` fingerprints, then load `CURRENT.md`, active hot entries, and task-relevant warm entries within the context budget. Use a full canonical read for migration, restore, audit, conflict resolution, durable writes, or any stale/missing index.
- Before every final reply, audit only durable deltas. For a real durable change, perform a full canonical read, write the narrow source entry, append `MEMORY_CHANGELOG.md`, atomically rebuild `MEMORY_INDEX.json`, run the health check, then mirror a compact summary with stable IDs through a verified native-memory file or API adapter.
- Exclude superseded, archived, and review-due entries from routine context. Treat candidates as hypotheses, require at least two independent evidence points before promoting a user impression, and never delete expired memory automatically.
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
    schema_version = data.get("schema_version")
    if schema_version not in {3, 4}:
        raise ValidationError("Unsupported schema_version; expected 3 or 4")
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
    if schema_version == 4:
        expected_lifecycle = {
            "lifecycle_index": "{}/{}".format(Path(package).name, MEMORY_INDEX),
            "runtime_loading": "selective-index",
        }
        for field, expected in expected_lifecycle.items():
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


def _today(value=None):
    if value is None:
        return datetime.now(timezone.utc).date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValidationError("Date must use YYYY-MM-DD: {}".format(value)) from exc


def _date_or_none(value):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _frontmatter_reviewed(text):
    match = FRONTMATTER_REVIEWED_RE.search(text)
    return match.group(1) if match else None


def _field_value(body, names):
    joined = "|".join(re.escape(name) for name in names)
    pattern = re.compile(
        r"(?m)^\s*-\s*(?:\*\*)?(?:{})(?:\*\*)?\s*[：:]\s*(.+?)\s*$".format(joined)
    )
    match = pattern.search(body)
    return match.group(1).strip() if match else None


def _normalize_status(raw):
    value = (raw or "active").strip().lower()
    if any(word in value for word in ("superseded", "废弃", "替代", "失效")):
        return "superseded"
    if any(word in value for word in ("archived", "归档")):
        return "archived"
    if any(word in value for word in ("review-due", "待复核", "到期")):
        return "review-due"
    if any(word in value for word in ("candidate", "候选", "待验证")):
        return "candidate"
    return "active"


def _default_tier(entry_id, status):
    if status in {"superseded", "archived"}:
        return "archive"
    prefix = entry_id.split("-", 1)[0]
    if prefix == "UP" and status == "active":
        return "hot"
    if prefix in {"MI"} or status == "candidate":
        return "cold"
    return "warm"


def _review_days(entry_id, status):
    if status in {"superseded", "archived"}:
        return None
    if status == "candidate":
        return 30
    prefix = entry_id.split("-", 1)[0]
    if prefix == "UI":
        return 60
    if prefix == "E":
        return 90
    if prefix == "D":
        return 365
    return 180


def _evidence_count(body):
    explicit = _field_value(body, ("证据数", "evidence_count"))
    if explicit and explicit.isdigit():
        return int(explicit)
    evidence_lines = re.findall(
        r"(?mi)^\s*-\s*(?:\*\*)?(?:来源证据|依据|证据)(?:\*\*)?\s*[：:].+$",
        body,
    )
    if not evidence_lines:
        return 0
    joined = " ".join(evidence_lines)
    if re.search(r"(?:两次|多次|至少\s*2|\b[2-9]\s*次)", joined):
        return 2
    return len(evidence_lines)


def _split_scope(raw):
    if not raw:
        return ["global"]
    values = [item.strip() for item in re.split(r"[,，、;/；]", raw) if item.strip()]
    return values or ["global"]


def _entry_summary(body):
    preferred = _field_value(
        body,
        ("内容", "结论", "决定", "正确结论", "环境", "观察", "经验", "规则"),
    )
    if preferred:
        return preferred[:500]
    for line in body.splitlines():
        cleaned = re.sub(r"^\s*-\s*", "", line).strip()
        if cleaned and not cleaned.startswith("#"):
            return cleaned[:500]
    return ""


def _parse_memory_entries(package):
    entries = []
    for source_name in ENTRY_SOURCE_FILES:
        path = Path(package) / source_name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        reviewed = _frontmatter_reviewed(text)
        matches = list(ENTRY_HEADING_RE.finditer(text))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[match.end():end]
            entry_id = match.group(1)
            status = _normalize_status(_field_value(body, ("状态", "status")))
            source_fields = set()
            raw_last_confirmed = _field_value(
                body, ("最后确认", "确认日期", "日期", "last_confirmed")
            )
            if _date_or_none(raw_last_confirmed):
                source_fields.add("last_confirmed")
            last_confirmed = (
                raw_last_confirmed if _date_or_none(raw_last_confirmed) else reviewed
            )
            raw_review_after = _field_value(body, ("复核日期", "review_after"))
            if _date_or_none(raw_review_after):
                source_fields.add("review_after")
            review_after = raw_review_after
            if not _date_or_none(review_after):
                days = _review_days(entry_id, status)
                confirmed_date = _date_or_none(last_confirmed)
                review_after = (
                    (confirmed_date + timedelta(days=days)).isoformat()
                    if days is not None and confirmed_date
                    else None
                )
            raw_scope = _field_value(body, ("适用范围", "范围", "scope"))
            if raw_scope:
                source_fields.add("scope")
            scope = _split_scope(raw_scope)
            raw_evidence_count = _field_value(body, ("证据数", "evidence_count"))
            if raw_evidence_count and raw_evidence_count.isdigit():
                source_fields.add("evidence_count")
            entries.append(
                {
                    "id": entry_id,
                    "title": match.group(2).strip(),
                    "source": source_name,
                    "status": status,
                    "tier": _default_tier(entry_id, status),
                    "scope": scope,
                    "load_when": list(scope),
                    "last_confirmed": last_confirmed,
                    "review_after": review_after,
                    "evidence_count": _evidence_count(body),
                    "summary": _entry_summary(body),
                    "_source_fields": sorted(source_fields),
                }
            )
    return entries


def _load_memory_index(package):
    path = Path(package) / MEMORY_INDEX
    if not path.is_file():
        raise ValidationError("Missing memory index: {}".format(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("Invalid memory index: {}".format(exc)) from exc
    if data.get("schema_version") != 1:
        raise ValidationError("Unsupported memory index schema_version; expected 1")
    if not isinstance(data.get("source_fingerprints"), dict):
        raise ValidationError("Memory index source_fingerprints must be an object")
    if not isinstance(data.get("entries"), list):
        raise ValidationError("Memory index entries must be a list")
    return data


def build_memory_index(vault_or_package, apply=False, today=None):
    """Build a deterministic source index while preserving reviewed lifecycle metadata."""
    _, package = _vault_and_package(vault_or_package)
    manifest = _load_manifest(package)
    if manifest.get("schema_version") != 4:
        raise ValidationError("build-index requires portability manifest schema_version 4")
    missing_sources = [name for name in INDEX_SOURCE_FILES if not (package / name).is_file()]
    if missing_sources:
        raise ValidationError("Cannot build memory index; missing: {}".format(", ".join(missing_sources)))

    previous = {}
    old_index = None
    index_path = package / MEMORY_INDEX
    if index_path.is_file():
        old_index = _load_memory_index(package)
        previous = {
            item.get("id"): item
            for item in old_index.get("entries", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }

    preserved_fields = (
        "tier",
        "scope",
        "load_when",
        "last_confirmed",
        "review_after",
        "evidence_count",
    )
    entries = _parse_memory_entries(package)
    for entry in entries:
        old = previous.get(entry["id"], {})
        source_fields = set(entry.pop("_source_fields", []))
        for field in preserved_fields:
            if field in old and field not in source_fields:
                entry[field] = old[field]
        if entry["status"] in {"superseded", "archived"}:
            entry["tier"] = "archive"

    duplicate_ids = sorted(
        entry_id
        for entry_id in {entry["id"] for entry in entries}
        if sum(item["id"] == entry_id for item in entries) > 1
    )
    if duplicate_ids:
        raise ValidationError("Duplicate stable memory IDs: {}".format(", ".join(duplicate_ids)))

    body = {
        "schema_version": 1,
        "source_fingerprints": {
            name: _sha256(package / name) for name in INDEX_SOURCE_FILES
        },
        "hot_budget_chars": DEFAULT_HOT_BUDGET_CHARS,
        "policy": {
            "current_stale_days": CURRENT_STALE_DAYS,
            "routine_statuses": ["active"],
            "excluded_statuses": ["review-due", "superseded", "archived"],
            "automatic_delete": False,
        },
        "entries": sorted(entries, key=lambda item: (item["source"], item["id"])),
    }
    if old_index:
        body["hot_budget_chars"] = old_index.get(
            "hot_budget_chars", DEFAULT_HOT_BUDGET_CHARS
        )
    old_body = dict(old_index) if old_index else None
    if old_body is not None:
        old_body.pop("generated_at", None)
    generated_at = (
        old_index.get("generated_at")
        if old_index and old_body == body and old_index.get("generated_at")
        else datetime.now(timezone.utc).isoformat()
    )
    payload = dict(body)
    payload["generated_at"] = generated_at
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    changed = not index_path.is_file() or index_path.read_text(encoding="utf-8") != content
    if apply:
        _atomic_write_text(index_path, content)
    return {
        "ok": True,
        "apply": bool(apply),
        "changed": changed,
        "index": str(index_path),
        "entry_count": len(entries),
        "source_count": len(INDEX_SOURCE_FILES),
    }


def memory_health(vault_or_package, today=None):
    """Audit lifecycle safety without modifying memory or deleting expired records."""
    _, package = _vault_and_package(vault_or_package)
    current_date = _today(today)
    errors = []
    warnings = []
    stale_sources = []
    review_due = []
    candidate_overdue = []
    impression_issues = []
    duplicate_ids = []
    try:
        index = _load_memory_index(package)
    except ValidationError as exc:
        return {
            "ok": False,
            "index_fresh": False,
            "stale_sources": [],
            "review_due": [],
            "candidate_overdue": [],
            "impression_issues": [],
            "duplicate_ids": [],
            "hot_chars": 0,
            "hot_budget_chars": DEFAULT_HOT_BUDGET_CHARS,
            "oversized_hot_context": False,
            "current_stale": True,
            "errors": [str(exc)],
            "warnings": [],
        }

    fingerprints = index["source_fingerprints"]
    for source_name in INDEX_SOURCE_FILES:
        path = package / source_name
        expected = fingerprints.get(source_name)
        if not path.is_file() or not expected or _sha256(path) != expected:
            stale_sources.append(source_name)
    if stale_sources:
        errors.append("Memory index is stale for: {}".format(", ".join(stale_sources)))

    seen = set()
    hot_chars = 0
    for position, entry in enumerate(index["entries"]):
        if not isinstance(entry, dict):
            errors.append("Memory index entry {} must be an object".format(position))
            continue
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id:
            errors.append("Memory index entry {} has no stable ID".format(position))
            continue
        if entry_id in seen:
            duplicate_ids.append(entry_id)
        seen.add(entry_id)
        status = entry.get("status")
        tier = entry.get("tier")
        if status not in VALID_ENTRY_STATUSES:
            errors.append("{} has invalid status {}".format(entry_id, status))
        if tier not in VALID_MEMORY_TIERS:
            errors.append("{} has invalid tier {}".format(entry_id, tier))
        due = _date_or_none(entry.get("review_after"))
        if due and due < current_date and status not in {"superseded", "archived"}:
            review_due.append(entry_id)
            if status == "candidate":
                candidate_overdue.append(entry_id)
        if entry_id.startswith("UI-") and status == "active":
            if (entry.get("evidence_count") or 0) < 2 or not due:
                impression_issues.append(entry_id)
        if tier == "hot" and status == "active" and entry_id not in review_due:
            hot_chars += len(entry.get("title", "")) + len(entry.get("summary", ""))

    if duplicate_ids:
        duplicate_ids = sorted(set(duplicate_ids))
        errors.append("Duplicate memory IDs: {}".format(", ".join(duplicate_ids)))
    if review_due:
        warnings.append("Review due: {}".format(", ".join(sorted(review_due))))
    if candidate_overdue:
        warnings.append("Candidate overdue: {}".format(", ".join(sorted(candidate_overdue))))
    if impression_issues:
        warnings.append(
            "Active impressions need two evidence points and a review date: {}".format(
                ", ".join(sorted(impression_issues))
            )
        )

    current_text = (package / "CURRENT.md").read_text(encoding="utf-8")
    current_reviewed = _date_or_none(_frontmatter_reviewed(current_text))
    current_stale = (
        current_reviewed is None
        or (current_date - current_reviewed).days > CURRENT_STALE_DAYS
    )
    if current_stale:
        warnings.append("CURRENT.md is stale or lacks a reviewed date")
    hot_budget = index.get("hot_budget_chars", DEFAULT_HOT_BUDGET_CHARS)
    if not isinstance(hot_budget, int) or hot_budget <= 0:
        errors.append("hot_budget_chars must be a positive integer")
        hot_budget = DEFAULT_HOT_BUDGET_CHARS
    oversized = hot_chars > hot_budget
    if oversized:
        warnings.append("Hot memory exceeds context budget")
    return {
        "ok": not errors,
        "index_fresh": not stale_sources,
        "stale_sources": sorted(stale_sources),
        "review_due": sorted(review_due),
        "candidate_overdue": sorted(candidate_overdue),
        "impression_issues": sorted(impression_issues),
        "duplicate_ids": duplicate_ids,
        "hot_chars": hot_chars,
        "hot_budget_chars": hot_budget,
        "oversized_hot_context": oversized,
        "current_stale": current_stale,
        "errors": errors,
        "warnings": warnings,
    }


def _query_terms(query):
    terms = set()
    for token in re.findall(r"[A-Za-z0-9_-]{2,}|[\u3400-\u9fff]{2,}", query.lower()):
        terms.add(token)
        if re.fullmatch(r"[\u3400-\u9fff]+", token) and len(token) > 2:
            for size in (2, 3, 4):
                for start in range(0, len(token) - size + 1):
                    terms.add(token[start:start + size])
    return terms


def _entry_relevance(entry, query_terms):
    haystack = " ".join(
        [
            str(entry.get("title", "")),
            str(entry.get("summary", "")),
            " ".join(entry.get("scope", [])),
            " ".join(entry.get("load_when", [])),
        ]
    ).lower()
    return sum(len(term) for term in query_terms if term in haystack)


def _minimum_relevance(query):
    cjk_tokens = re.findall(r"[\u3400-\u9fff]+", query)
    return 4 if len(cjk_tokens) == 1 and len(cjk_tokens[0]) >= 4 else 1


def runtime_context(vault_or_package, query, max_chars=DEFAULT_HOT_BUDGET_CHARS, today=None):
    """Return bounded current, hot, and query-relevant memory; fail on stale indexes."""
    if not isinstance(query, str) or not query.strip():
        raise ValidationError("runtime-context requires a non-empty query")
    if not isinstance(max_chars, int) or max_chars < 500:
        raise ValidationError("max_chars must be an integer of at least 500")
    _, package = _vault_and_package(vault_or_package)
    health = memory_health(package, today=today)
    if not health["ok"] or not health["index_fresh"]:
        raise ValidationError(
            "Memory index is missing or stale; rebuild it after a full canonical read"
        )
    index = _load_memory_index(package)
    due_ids = set(health["review_due"])
    terms = _query_terms(query)
    minimum_relevance = _minimum_relevance(query)
    candidates = []
    for entry in index["entries"]:
        if entry.get("status") != "active" or entry.get("id") in due_ids:
            continue
        tier = entry.get("tier")
        score = _entry_relevance(entry, terms)
        if tier == "hot" or (tier == "warm" and score >= minimum_relevance):
            candidates.append((0 if tier == "hot" else 1, -score, entry["id"], entry))
    candidates.sort(key=lambda item: item[:3])

    current = (package / "CURRENT.md").read_text(encoding="utf-8").strip()
    prefix = "# Runtime continuity context\n\nQuery: {}\n".format(query.strip())
    if health["current_stale"]:
        prefix += "\nWarning: CURRENT.md is review-due; verify it before relying on it.\n"
    prefix += "\n## CURRENT.md\n\n"
    if len(prefix) + len(current) > max_chars:
        remaining = max(0, max_chars - len(prefix) - 32)
        current = current[:remaining] + "\n[CURRENT truncated]"
    context = prefix + current
    loaded_ids = []
    skipped_budget = []
    for _, _, entry_id, entry in candidates:
        block = "\n\n## {}：{}\n\n- 来源：{}\n- 层级：{}\n- 摘要：{}".format(
            entry_id,
            entry.get("title", ""),
            entry.get("source", ""),
            entry.get("tier", ""),
            entry.get("summary", ""),
        )
        if len(context) + len(block) > max_chars:
            skipped_budget.append(entry_id)
            continue
        context += block
        loaded_ids.append(entry_id)
    return {
        "ok": True,
        "query": query.strip(),
        "loaded_ids": loaded_ids,
        "review_due_ids": health["review_due"],
        "skipped_budget_ids": skipped_budget,
        "current_stale": health["current_stale"],
        "context_chars": len(context),
        "max_chars": max_chars,
        "context": context,
        "warnings": health["warnings"],
    }


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
        if manifest.get("schema_version") == 4:
            lifecycle = memory_health(package)
            if not lifecycle["ok"]:
                errors.extend(
                    "Memory index: {}".format(error) for error in lifecycle["errors"]
                )
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
3. Validate `MEMORY_INDEX.json`; use bounded selective loading for ordinary work and a full canonical
   read for restore, writes, audits, conflicts, onboarding, or stale-index recovery.
4. Load domain context only when its activation condition applies.
5. Install or present `skills/*/*/SKILL.md` to the new agent; merge rules semantically and never
   overwrite unrelated local rules.
6. Discover the new agent's documented persistent-rule and native-memory interfaces. Preview
   `bootstrap-agent` before applying it; never invent a `MEMORY.md` path.
7. Run a read-only restoration check before making changes. Preserve conflicts for user review.
8. Pull Obsidian context before work. Before the final reply, write warranted durable deltas to
   Obsidian, append the changelog, rebuild and health-check the index, then update a verified
   local-memory mirror using the same stable IDs.
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

    build_index = sub.add_parser(
        "build-index", help="Preview or atomically rebuild the lifecycle memory index"
    )
    build_index.add_argument("--vault", required=True)
    build_index.add_argument("--apply", action="store_true")

    health = sub.add_parser(
        "memory-health", help="Audit freshness, lifecycle, evidence, and context budget"
    )
    health.add_argument("--vault", required=True)

    runtime = sub.add_parser(
        "runtime-context", help="Load bounded current, hot, and task-relevant memory"
    )
    runtime.add_argument("--vault", required=True)
    runtime.add_argument("--query", required=True)
    runtime.add_argument("--max-chars", type=int, default=DEFAULT_HOT_BUDGET_CHARS)
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
        elif args.command == "build-index":
            report = build_memory_index(args.vault, apply=args.apply)
        elif args.command == "memory-health":
            report = memory_health(args.vault)
        elif args.command == "runtime-context":
            report = runtime_context(args.vault, args.query, max_chars=args.max_chars)
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
