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


if __name__ == "__main__":
    unittest.main()
