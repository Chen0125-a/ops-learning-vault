import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "continuity.py"


def load_module():
    spec = importlib.util.spec_from_file_location("continuity", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write(path: Path, content: str = "ok\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def fake_private_key_marker() -> str:
    return "-----BEGIN " + "PRIVATE KEY-----\nabc\n"


def create_vault(base: Path) -> Path:
    vault = base / "vault"
    package = vault / "AI协作-通用记忆包"
    package.mkdir(parents=True)
    required = [
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
        "PORTABLE_MEMORY_POLICY.md",
    ]
    for name in required:
        write(package / name, f"---\nreviewed: 2026-07-26\n---\n# {name}\n")

    manifest = {
        "schema_version": 3,
        "package_id": "portable-agent-continuity",
        "memory_package": "AI协作-通用记忆包",
        "context_paths": [
            {"path": "AI协作-通用记忆包", "role": "general-memory", "required": True},
            {"path": "AGENTS.md", "role": "portable-rules", "required": True},
        ],
        "required_skills": ["obsidian-user-memory", "yunwei-teacher"],
        "managed_skill_sets": [],
        "memory_protocol": {
            "canonical_store": "obsidian",
            "policy": "AI协作-通用记忆包/PORTABLE_MEMORY_POLICY.md",
            "agent_registry": "AI协作-通用记忆包/AGENT_MEMORY_REGISTRY.json",
            "sync_order": ["pull-before-work", "push-before-final-reply"],
        },
        "last_verified": "2026-07-26",
    }
    write(package / "PORTABILITY_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    registry = {
        "schema_version": 1,
        "canonical_store": "obsidian",
        "agents": [],
    }
    write(package / "AGENT_MEMORY_REGISTRY.json", json.dumps(registry, ensure_ascii=False, indent=2))
    write(vault / "AGENTS.md", "# Portable rules\n")
    return vault


def create_skill(root: Path, name: str) -> None:
    write(
        root / name / "SKILL.md",
        f"---\nname: {name}\ndescription: Test skill {name}.\n---\n\n# {name}\n",
    )


def update_manifest(vault: Path, transform) -> None:
    path = vault / "AI协作-通用记忆包" / "PORTABILITY_MANIFEST.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    transform(data)
    write(path, json.dumps(data, ensure_ascii=False, indent=2))


def enable_lifecycle_v4(vault: Path) -> None:
    def transform(data):
        data["schema_version"] = 4
        data["memory_protocol"].update(
            {
                "lifecycle_index": "AI协作-通用记忆包/MEMORY_INDEX.json",
                "runtime_loading": "selective-index",
            }
        )

    update_manifest(vault, transform)


def seed_lifecycle_memory(vault: Path) -> Path:
    package = vault / "AI协作-通用记忆包"
    write(
        package / "CURRENT.md",
        "---\nreviewed: 2026-07-27\n---\n# Current\n\n正在维护可迁移记忆。\n",
    )
    write(
        package / "USER_PROFILE.md",
        """---
reviewed: 2026-07-27
---
# User profile

## UP-001：偏好直接交付

- 状态：active
- 内容：优先直接完成可逆任务。
- 来源证据：用户在多个任务中重复确认。

## UP-002：已废弃旧偏好

- 状态：superseded
- 内容：旧结论，不应再加载。
""",
    )
    write(
        package / "COLLABORATION_MEMORY.md",
        """---
reviewed: 2026-07-27
---
# Collaboration memory

## UI-001：偏好简洁表达

- 状态：active
- 观察：用户通常偏好结论先行。
- 来源证据：两次独立任务中的明确反馈。

## UI-002：一次性印象

- 状态：candidate
- 观察：可能喜欢非常长的回答。
- 来源证据：一次临时请求。
""",
    )
    write(
        package / "LESSONS.md",
        """---
reviewed: 2026-07-27
---
# Lessons

## L-001：迁移后先验证

- 状态：active
- 正确结论：恢复后应先做只读验收。
- 适用范围：迁移、恢复、换机

## L-002：无关的数据库经验

- 状态：active
- 正确结论：数据库迁移前先备份。
- 适用范围：数据库
""",
    )
    return package


class ContinuityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_discover_memory_package_from_vault_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = create_vault(Path(tmp))
            found = self.mod.discover_memory_package(explicit=vault)
            self.assertEqual(found, vault / "AI协作-通用记忆包")

    def test_verify_package_and_required_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            skills = base / "skills"
            create_skill(skills, "obsidian-user-memory")
            create_skill(skills, "yunwei-teacher")

            report = self.mod.verify_package(vault, skill_roots=[skills])

            self.assertTrue(report["ok"])
            self.assertEqual(report["missing_files"], [])
            self.assertEqual(report["missing_skills"], [])

    def test_verify_reports_missing_file_and_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            (vault / "AI协作-通用记忆包" / "LESSONS.md").unlink()

            report = self.mod.verify_package(vault, skill_roots=[base / "empty-skills"])

            self.assertFalse(report["ok"])
            self.assertIn("LESSONS.md", report["missing_files"])
            self.assertIn("obsidian-user-memory", report["missing_skills"])

    def test_verify_requires_dual_memory_policy_and_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            package = vault / "AI协作-通用记忆包"
            (package / "PORTABLE_MEMORY_POLICY.md").unlink()
            (package / "AGENT_MEMORY_REGISTRY.json").unlink()

            report = self.mod.verify_package(vault)

            self.assertFalse(report["ok"])
            self.assertIn("PORTABLE_MEMORY_POLICY.md", report["missing_files"])
            self.assertIn("AGENT_MEMORY_REGISTRY.json", report["missing_files"])

    def test_verify_rejects_invalid_agent_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = create_vault(Path(tmp))
            package = vault / "AI协作-通用记忆包"
            write(
                package / "AGENT_MEMORY_REGISTRY.json",
                json.dumps(
                    {
                        "schema_version": 1,
                        "canonical_store": "agent-local",
                        "agents": [{"agent_id": "duplicate"}, {"agent_id": "duplicate"}],
                    }
                ),
            )

            report = self.mod.verify_package(vault)

            self.assertFalse(report["ok"])
            self.assertTrue(any("AGENT_MEMORY_REGISTRY" in error for error in report["errors"]))

    def test_bootstrap_agent_is_dry_run_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            rules = base / "agent-home" / "RULES.md"
            original = "# Existing rules\n\nKeep this rule.\n"
            write(rules, original)

            report = self.mod.bootstrap_agent(
                vault,
                agent_id="example-agent",
                product="Example Agent",
                rules_file=rules,
                native_memory_paths=[],
                apply=False,
            )

            self.assertTrue(report["ok"])
            self.assertFalse(report["apply"])
            self.assertEqual(rules.read_text(encoding="utf-8"), original)
            registry = json.loads(
                (vault / "AI协作-通用记忆包" / "AGENT_MEMORY_REGISTRY.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(registry["agents"], [])

    def test_bootstrap_agent_apply_preserves_rules_registers_degraded_mode_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            rules = base / "agent-home" / "RULES.md"
            original = "# Existing rules\n\nKeep this rule.\n"
            write(rules, original)

            first = self.mod.bootstrap_agent(
                vault,
                agent_id="example-agent",
                product="Example Agent",
                rules_file=rules,
                native_memory_paths=[],
                apply=True,
            )
            second = self.mod.bootstrap_agent(
                vault,
                agent_id="example-agent",
                product="Example Agent",
                rules_file=rules,
                native_memory_paths=[],
                apply=True,
            )

            content = rules.read_text(encoding="utf-8")
            self.assertTrue(first["ok"])
            self.assertTrue(second["ok"])
            self.assertIn(original.strip(), content)
            self.assertEqual(content.count(self.mod.POLICY_BEGIN), 1)
            self.assertEqual(content.count(self.mod.POLICY_END), 1)
            registry = json.loads(
                (vault / "AI协作-通用记忆包" / "AGENT_MEMORY_REGISTRY.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(registry["agents"]), 1)
            self.assertEqual(registry["agents"][0]["agent_id"], "example-agent")
            self.assertEqual(
                registry["agents"][0]["dual_memory_status"],
                "degraded-no-native-memory-file",
            )

    def test_bootstrap_agent_registers_verified_native_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            rules = base / "agent-home" / "RULES.md"
            memory = base / "agent-home" / "MEMORY.md"
            write(rules, "# Rules\n")
            write(memory, "# Native memory\n")

            preview = self.mod.bootstrap_agent(
                vault,
                agent_id="memory-agent",
                product="Memory Agent",
                rules_file=rules,
                native_memory_paths=[memory],
                native_memory_verified=False,
                apply=False,
            )
            report = self.mod.bootstrap_agent(
                vault,
                agent_id="memory-agent",
                product="Memory Agent",
                rules_file=rules,
                native_memory_paths=[memory],
                rules_autoload_verified=True,
                native_memory_verified=True,
                apply=True,
            )

            self.assertEqual(
                preview["dual_memory_status"],
                "degraded-unverified-native-memory-path",
            )
            self.assertTrue(report["ok"])
            self.assertEqual(report["dual_memory_status"], "verified")
            registry = json.loads(
                (vault / "AI协作-通用记忆包" / "AGENT_MEMORY_REGISTRY.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(registry["agents"][0]["dual_memory_status"], "verified")
            self.assertEqual(len(registry["agents"][0]["native_memory_paths"]), 1)
            self.assertEqual(
                registry["agents"][0]["native_memory_verification"]["method"],
                "create-read-update-roundtrip",
            )
            self.assertEqual(registry["agents"][0]["rules_autoload"], "verified")

    def test_bootstrap_agent_requires_roundtrip_confirmation_for_api_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            rules = base / "agent-home" / "RULES.md"
            write(rules, "# Rules\n")

            preview = self.mod.bootstrap_agent(
                vault,
                agent_id="api-agent",
                product="API Memory Agent",
                rules_file=rules,
                native_memory_paths=[],
                native_memory_adapter="documented-memory-api",
                native_memory_verified=False,
                apply=False,
            )
            applied = self.mod.bootstrap_agent(
                vault,
                agent_id="api-agent",
                product="API Memory Agent",
                rules_file=rules,
                native_memory_paths=[],
                native_memory_adapter="documented-memory-api",
                rules_autoload_verified=True,
                native_memory_verified=True,
                apply=True,
            )

            self.assertEqual(
                preview["dual_memory_status"],
                "degraded-unverified-native-memory-adapter",
            )
            self.assertEqual(applied["dual_memory_status"], "verified")
            registry = json.loads(
                (vault / "AI协作-通用记忆包" / "AGENT_MEMORY_REGISTRY.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(registry["agents"][0]["native_memory_mode"], "api-adapter")
            self.assertEqual(
                registry["agents"][0]["native_memory_adapter"],
                "documented-memory-api",
            )
            self.assertEqual(
                registry["agents"][0]["native_memory_verification"]["status"],
                "verified",
            )

    def test_bootstrap_agent_refuses_to_replace_conflicting_policy_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            rules = base / "agent-home" / "RULES.md"
            original = (
                "# Rules\n\n"
                + self.mod.POLICY_BEGIN
                + "\nA different policy\n"
                + self.mod.POLICY_END
                + "\n"
            )
            write(rules, original)

            report = self.mod.bootstrap_agent(
                vault,
                agent_id="conflict-agent",
                product="Conflict Agent",
                rules_file=rules,
                native_memory_paths=[],
                apply=True,
            )

            self.assertFalse(report["ok"])
            self.assertEqual(report["status"], "conflict")
            self.assertEqual(rules.read_text(encoding="utf-8"), original)

    def test_verify_scans_allowlisted_context_outside_memory_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            skills = base / "skills"
            create_skill(skills, "obsidian-user-memory")
            create_skill(skills, "yunwei-teacher")
            write(vault / "AGENTS.md", fake_private_key_marker())

            report = self.mod.verify_package(vault, skill_roots=[skills])

            self.assertFalse(report["ok"])
            self.assertTrue(
                any(item["kind"] == "high-confidence-secret" for item in report["security_findings"])
            )

    def test_verify_rejects_invalid_managed_skill_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            skills = base / "skills"
            create_skill(skills, "obsidian-user-memory")
            create_skill(skills, "yunwei-teacher")
            update_manifest(
                vault,
                lambda data: data.update(
                    {
                        "managed_skill_sets": [
                            {
                                "name": "bad-set",
                                "source_type": "mixed-repositories",
                                "sources": ["https://example.invalid/repo.git"],
                                "restore": "reinstall",
                                "required": True,
                                "inventory": ["managed-one"],
                            }
                        ]
                    }
                ),
            )

            report = self.mod.verify_package(vault, skill_roots=[skills])

            self.assertFalse(report["ok"])
            self.assertTrue(any("managed_skill_sets" in error for error in report["errors"]))

    def test_verify_reports_missing_required_managed_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            skills = base / "skills"
            create_skill(skills, "obsidian-user-memory")
            create_skill(skills, "yunwei-teacher")
            update_manifest(
                vault,
                lambda data: data.update(
                    {
                        "managed_skill_sets": [
                            {
                                "name": "local-fallback",
                                "source_type": "local-inventory",
                                "source": "current user Skill root",
                                "restore": "restore from verified bundle",
                                "bundle_group": "agent-user",
                                "required": True,
                                "inventory": ["managed-one"],
                            }
                        ]
                    }
                ),
            )

            report = self.mod.verify_package(vault, skill_roots=[skills])

            self.assertFalse(report["ok"])
            self.assertEqual(report["missing_managed_skills"], ["managed-one"])

    def test_secret_scan_blocks_private_key_and_forbidden_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            write(base / "auth.json", "{}")
            write(base / "notes.md", fake_private_key_marker())

            findings = self.mod.scan_for_secrets([base])

            kinds = {item["kind"] for item in findings}
            self.assertIn("forbidden-name", kinds)
            self.assertIn("high-confidence-secret", kinds)

    def test_skill_source_does_not_trigger_its_own_secret_scan(self):
        findings = self.mod.scan_for_secrets([Path(__file__).parents[1]])
        self.assertEqual(findings, [])

    def test_export_bundle_copies_allowlisted_context_and_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            skill_root = base / "skills"
            create_skill(skill_root, "obsidian-user-memory")
            create_skill(skill_root, "yunwei-teacher")
            write(skill_root / ".system" / "internal.txt", "do not copy")
            output = base / "bundle"

            report = self.mod.export_bundle(
                vault_root=vault,
                output=output,
                skill_roots={"codex-user": skill_root},
            )

            self.assertTrue(report["ok"])
            self.assertTrue((output / "vault" / "AGENTS.md").is_file())
            self.assertTrue(
                (output / "skills" / "codex-user" / "obsidian-user-memory" / "SKILL.md").is_file()
            )
            self.assertFalse((output / "skills" / "codex-user" / ".system").exists())
            self.assertTrue((output / "checksums.sha256").is_file())
            self.assertTrue((output / "HANDOFF.md").is_file())

    def test_export_fails_closed_when_secret_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            skill_root = base / "skills"
            create_skill(skill_root, "obsidian-user-memory")
            create_skill(skill_root, "yunwei-teacher")
            write(vault / "AI协作-通用记忆包" / "auth.json", "{}")

            with self.assertRaises(self.mod.SecurityError):
                self.mod.export_bundle(vault, base / "bundle", {"codex-user": skill_root})

            self.assertFalse((base / "bundle").exists())

    def test_verify_bundle_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            skill_root = base / "skills"
            create_skill(skill_root, "obsidian-user-memory")
            create_skill(skill_root, "yunwei-teacher")
            output = base / "bundle"
            self.mod.export_bundle(vault, output, {"codex-user": skill_root})
            write(output / "vault" / "AGENTS.md", "tampered\n")

            report = self.mod.verify_bundle(output)

            self.assertFalse(report["ok"])
            self.assertIn("vault/AGENTS.md", report["mismatched"])

    def test_restore_is_dry_run_by_default_and_apply_never_overwrites_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            skill_root = base / "skills"
            create_skill(skill_root, "obsidian-user-memory")
            create_skill(skill_root, "yunwei-teacher")
            bundle = base / "bundle"
            self.mod.export_bundle(vault, bundle, {"codex-user": skill_root})
            target_vault = base / "new-vault"
            target_skills = base / "new-skills"

            preview = self.mod.restore_bundle(
                bundle,
                target_vault,
                {"codex-user": target_skills},
                apply=False,
            )
            self.assertTrue(preview["ok"])
            self.assertFalse(target_vault.exists())

            applied = self.mod.restore_bundle(
                bundle,
                target_vault,
                {"codex-user": target_skills},
                apply=True,
            )
            self.assertTrue(applied["ok"])
            self.assertTrue((target_vault / "AGENTS.md").is_file())
            installed = target_skills / "obsidian-user-memory" / "SKILL.md"
            self.assertTrue(installed.is_file())

            write(installed, "local conflicting version\n")
            conflict = self.mod.restore_bundle(
                bundle,
                target_vault,
                {"codex-user": target_skills},
                apply=True,
            )
            self.assertFalse(conflict["ok"])
            self.assertIn("skills/codex-user/obsidian-user-memory/SKILL.md", conflict["conflicts"])
            self.assertEqual(installed.read_text(encoding="utf-8"), "local conflicting version\n")

    def test_cli_entrypoints_cover_discover_verify_export_and_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vault = create_vault(base)
            skills = base / "skills"
            create_skill(skills, "obsidian-user-memory")
            create_skill(skills, "yunwei-teacher")
            rules = base / "RULES.md"
            write(rules, "# Rules\n")
            bundle = base / "bundle"
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                discover_code = self.mod.main(["discover", "--vault", str(vault)])
                verify_code = self.mod.main(
                    ["verify", "--vault", str(vault), "--skill-root", str(skills)]
                )
                export_code = self.mod.main(
                    [
                        "export",
                        "--vault",
                        str(vault),
                        "--output",
                        str(bundle),
                        "--skill-root",
                        "test={}".format(skills),
                    ]
                )
                bundle_code = self.mod.main(
                    ["verify-bundle", "--bundle", str(bundle)]
                )
                bootstrap_code = self.mod.main(
                    [
                        "bootstrap-agent",
                        "--vault",
                        str(vault),
                        "--agent-id",
                        "cli-agent",
                        "--product",
                        "CLI Agent",
                        "--rules-file",
                        str(rules),
                    ]
                )
                invalid_code = self.mod.main(
                    [
                        "export",
                        "--vault",
                        str(vault),
                        "--output",
                        str(base / "bad-bundle"),
                        "--skill-root",
                        "invalid-mapping",
                    ]
                )

            self.assertEqual(discover_code, 0)
            self.assertEqual(verify_code, 0)
            self.assertEqual(export_code, 0)
            self.assertEqual(bundle_code, 0)
            self.assertEqual(bootstrap_code, 0)
            self.assertEqual(invalid_code, 2)
            self.assertIn("requires LABEL=PATH", stderr.getvalue())

    def test_build_memory_index_is_dry_run_then_atomic_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = create_vault(Path(tmp))
            package = seed_lifecycle_memory(vault)
            enable_lifecycle_v4(vault)

            preview = self.mod.build_memory_index(vault, apply=False)

            self.assertTrue(preview["ok"])
            self.assertFalse(preview["apply"])
            self.assertFalse((package / "MEMORY_INDEX.json").exists())
            self.assertGreaterEqual(preview["entry_count"], 6)

            applied = self.mod.build_memory_index(vault, apply=True)
            index = json.loads((package / "MEMORY_INDEX.json").read_text(encoding="utf-8"))
            by_id = {entry["id"]: entry for entry in index["entries"]}

            self.assertTrue(applied["ok"])
            self.assertEqual(index["schema_version"], 1)
            self.assertEqual(by_id["UP-001"]["tier"], "hot")
            self.assertEqual(by_id["UI-001"]["tier"], "warm")
            self.assertEqual(by_id["UP-002"]["status"], "superseded")
            self.assertEqual(by_id["UP-002"]["tier"], "archive")
            self.assertIn("CURRENT.md", index["source_fingerprints"])

    def test_rebuilding_unchanged_index_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = create_vault(Path(tmp))
            package = seed_lifecycle_memory(vault)
            enable_lifecycle_v4(vault)
            self.mod.build_memory_index(vault, apply=True)
            first = (package / "MEMORY_INDEX.json").read_text(encoding="utf-8")

            second_report = self.mod.build_memory_index(vault, apply=True)
            second = (package / "MEMORY_INDEX.json").read_text(encoding="utf-8")

            self.assertFalse(second_report["changed"])
            self.assertEqual(second, first)

    def test_index_fingerprint_detects_source_drift_and_verify_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = create_vault(Path(tmp))
            package = seed_lifecycle_memory(vault)
            enable_lifecycle_v4(vault)
            self.mod.build_memory_index(vault, apply=True)
            with (package / "LESSONS.md").open("a", encoding="utf-8") as stream:
                stream.write("\n新内容使索引过期。\n")

            health = self.mod.memory_health(vault)
            report = self.mod.verify_package(vault)

            self.assertFalse(health["ok"])
            self.assertIn("LESSONS.md", health["stale_sources"])
            self.assertFalse(report["ok"])
            self.assertTrue(any("memory index" in error.lower() for error in report["errors"]))
            with self.assertRaises(self.mod.ValidationError):
                self.mod.runtime_context(vault, query="迁移恢复")

    def test_runtime_context_is_selective_and_excludes_due_or_superseded_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = create_vault(Path(tmp))
            package = seed_lifecycle_memory(vault)
            enable_lifecycle_v4(vault)
            self.mod.build_memory_index(vault, apply=True)
            index_path = package / "MEMORY_INDEX.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            for entry in index["entries"]:
                if entry["id"] == "UI-001":
                    entry["review_after"] = "2026-07-26"
            write(index_path, json.dumps(index, ensure_ascii=False, indent=2) + "\n")

            result = self.mod.runtime_context(
                vault,
                query="迁移恢复",
                max_chars=5000,
                today="2026-07-27",
            )

            self.assertTrue(result["ok"])
            self.assertIn("UP-001", result["loaded_ids"])
            self.assertIn("L-001", result["loaded_ids"])
            self.assertNotIn("L-002", result["loaded_ids"])
            self.assertNotIn("UP-002", result["loaded_ids"])
            self.assertNotIn("UI-001", result["loaded_ids"])
            self.assertIn("UI-001", result["review_due_ids"])
            self.assertLessEqual(result["context_chars"], 5000)

    def test_memory_health_flags_unsafe_impression_candidate_and_hot_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = create_vault(Path(tmp))
            package = seed_lifecycle_memory(vault)
            enable_lifecycle_v4(vault)
            self.mod.build_memory_index(vault, apply=True)
            index_path = package / "MEMORY_INDEX.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["hot_budget_chars"] = 10
            for entry in index["entries"]:
                if entry["id"] == "UI-001":
                    entry["evidence_count"] = 1
                    entry["review_after"] = None
                if entry["id"] == "UI-002":
                    entry["last_confirmed"] = "2026-01-01"
                    entry["review_after"] = "2026-01-31"
            write(index_path, json.dumps(index, ensure_ascii=False, indent=2) + "\n")

            health = self.mod.memory_health(vault, today="2026-07-27")

            self.assertTrue(health["index_fresh"])
            self.assertTrue(health["oversized_hot_context"])
            self.assertIn("UI-001", health["impression_issues"])
            self.assertIn("UI-002", health["candidate_overdue"])
            self.assertGreaterEqual(len(health["warnings"]), 3)

    def test_v4_manifest_requires_lifecycle_index_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = create_vault(Path(tmp))
            update_manifest(vault, lambda data: data.update({"schema_version": 4}))

            report = self.mod.verify_package(vault)

            self.assertFalse(report["ok"])
            self.assertTrue(any("lifecycle_index" in error for error in report["errors"]))

    def test_cli_entrypoints_cover_index_health_and_runtime_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = create_vault(Path(tmp))
            seed_lifecycle_memory(vault)
            enable_lifecycle_v4(vault)
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                build_code = self.mod.main(
                    ["build-index", "--vault", str(vault), "--apply"]
                )
                health_code = self.mod.main(["memory-health", "--vault", str(vault)])
                context_code = self.mod.main(
                    [
                        "runtime-context",
                        "--vault",
                        str(vault),
                        "--query",
                        "迁移恢复",
                        "--max-chars",
                        "5000",
                    ]
                )

            self.assertEqual(build_code, 0)
            self.assertEqual(health_code, 0)
            self.assertEqual(context_code, 0)
            self.assertIn('"loaded_ids"', stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
