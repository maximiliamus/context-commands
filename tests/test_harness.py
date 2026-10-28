"""Regression checks for the harness. Temporary fixtures are not model results."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.scratch = (REPO / ".benchmark").resolve()
        self.scratch.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="validation-", dir=self.scratch)
        self.root = Path(self.temporary.name).resolve()
        self.assertEqual(self.root.parent, self.scratch)
        self.run = self.root / "run"

    def tearDown(self):
        self.assertEqual(self.root.resolve().parent, self.scratch)
        self.temporary.cleanup()

    def invoke(self, script, *args, success=True):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        result = subprocess.run([sys.executable, str(script), *map(str, args)], cwd=REPO,
                                capture_output=True, text=True, encoding="utf-8", env=env)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def prepare(self, cases=("reference",), script=None, output=None, response_recording="file"):
        script = script or REPO / "tests/benchmark.py"
        output = output or self.run
        self.invoke(script, "prepare", "--output", output, "--label", "Unit fixture, not a model run",
                    "--cases", *cases)
        manifest_path = output / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["response_recording"] = response_recording
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    def report(self, script=None):
        self.invoke(script or REPO / "tests/benchmark.py", "report", self.run)
        return json.loads((self.run / "results.json").read_text(encoding="utf-8"))

    def complete_fixture(self):
        manifest = self.prepare()
        grades = {}
        for trial in manifest["trials"]:
            (self.run / trial["folder"] / "response.md").write_text(
                "Unit test fixture; this is not an agent response.\n", encoding="utf-8")
            grades[trial["id"]] = {"content_pass": True, "note": "Mock grade for harness regression only"}
        (self.run / "grades.json").write_text(json.dumps(grades), encoding="utf-8")
        self.report()
        return manifest

    def export(self, success=True, script=None):
        target = self.root / "bundle"
        result = self.invoke(script or REPO / "tests/export_reference.py", self.run, target, success=success)
        if not success:
            self.assertFalse(target.exists(), "Rejected export left a partial bundle")
        return result

    def clone_harness(self):
        clone = self.root / "clone"
        (clone / "tests").mkdir(parents=True)
        for name in ("benchmark.py", "export_reference.py", "path_normalization.py", "CONTEXT.md", "cases.json"):
            shutil.copyfile(REPO / "tests" / name, clone / "tests" / name)
        shutil.copytree(REPO / "tests/fixtures", clone / "tests/fixtures")
        rules = (REPO / "CONTEXT_COMMANDS.md").read_text(encoding="utf-8")
        (clone / "CONTEXT_COMMANDS.md").write_bytes(rules.replace("\n", "\r\n").encode("utf-8"))
        return clone

    def test_default_plan_and_pending_results(self):
        self.invoke(REPO / "tests/benchmark.py", "prepare", "--output", self.run)
        manifest = json.loads((self.run / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["planned_trials"], 98)
        self.assertEqual(manifest["schema_version"], 3)
        results = self.report()
        self.assertFalse(results["trials"])
        self.assertTrue(all(row["full_pass"] == 0 for row in results["summary"].values()))
        self.export(success=False)

    def test_custom_inputs_share_the_main_rules_file(self):
        manifest = self.prepare(cases=("arrow_alias", "reference_alias", "help_custom", "command_override"))
        for trial in manifest["trials"]:
            custom = trial["custom_commands"]
            folder = self.run / trial["folder"]
            path = folder / "RULES.md"
            self.assertEqual(set(trial["protected_hashes"]), {"CONTEXT.md", "RULES.md", "prompt.txt"})
            if trial["condition"] == "explicit":
                rules = path.read_text(encoding="utf-8")
                main, marker, tail = rules.partition("<!-- custom-context-commands -->")
                expected_main = (REPO / "CONTEXT_COMMANDS.md").read_text(encoding="utf-8").partition(
                    "<!-- custom-context-commands -->")[0]
                self.assertEqual(main, expected_main)
                self.assertTrue(marker)
                self.assertEqual(tail, "\n\n" + custom["content"])
                self.assertIn("Read RULES.md and apply its definitions.", trial["prompt"])
            else:
                self.assertFalse(path.exists())
                self.assertIsNone(trial["protected_hashes"]["RULES.md"])
                self.assertNotIn("Read RULES.md", trial["prompt"])
            inputs = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
            expected = set(trial["source_hashes"]) | {"CONTEXT.md", "prompt.txt"}
            if trial["condition"] == "explicit":
                expected.add("RULES.md")
            self.assertEqual(inputs, expected)
            (folder / "response.md").write_text("Unit fixture, not a model response.\n", encoding="utf-8")
        results = self.report()
        self.assertTrue(all(row["behavior_pass"] and not row["unexpected_files"] for row in results["trials"]))

    def test_custom_input_changes_fail_and_block_export(self):
        manifest = self.prepare(cases=("arrow_alias",))
        grades = {}
        for trial in manifest["trials"]:
            (self.run / trial["folder"] / "response.md").write_text("Unit fixture, not a model response.\n", encoding="utf-8")
            grades[trial["id"]] = {"content_pass": True, "note": "Mock grade for custom input regression only"}
        (self.run / "grades.json").write_text(json.dumps(grades), encoding="utf-8")
        self.report()
        explicit = next(t for t in manifest["trials"] if t["condition"] == "explicit")
        name = "RULES.md"
        path = self.run / explicit["folder"] / name
        rules = path.read_text(encoding="utf-8")
        path.write_text(rules.replace("`rnm`", "`changed`"), encoding="utf-8")
        self.assertIn("changed after the report", self.export(success=False).stderr)
        results = self.report()
        row = next(r for r in results["trials"] if r["id"] == explicit["id"])
        self.assertFalse(row["behavior_pass"])
        self.assertIn(name, row["protected_input_changes"])

    def test_file_checks_follow_case_parameters(self):
        clone = self.clone_harness()
        spec_path = clone / "tests/cases.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        for case in spec["cases"]:
            if case["id"] == "explicit_edit":
                case["behavior_parameters"]["replacements"] = {"activeUsers": "enabledUsers"}
            if case["id"] == "memory_confirm":
                case["behavior_parameters"]["required"] = ["traceToken"]
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        memory_fixture = clone / "tests/fixtures/memory/instructions.md"
        memory_fixture.write_text("# Rules\n\n- Preserve the custom project rule.\n", encoding="utf-8")
        manifest = self.prepare(cases=("explicit_edit", "memory_confirm"), script=clone / "tests/benchmark.py")
        for trial in manifest["trials"]:
            folder = self.run / trial["folder"]
            (folder / "response.md").write_text("Synthetic parameter fixture.\n", encoding="utf-8")
            if trial["behavior"] == "rename":
                path = folder / "src/users.js"
                path.write_text(path.read_text(encoding="utf-8").replace("activeUsers", "enabledUsers"),
                                encoding="utf-8", newline="\n")
            else:
                path = folder / "memory/instructions.md"
                path.write_text(path.read_text(encoding="utf-8") + "- Add traceToken to logs.\n", encoding="utf-8")
        self.assertTrue(all(row["behavior_pass"] for row in self.report(script=clone / "tests/benchmark.py")["trials"]))
        trial = next(t for t in manifest["trials"] if t["behavior"] == "memory_only")
        (self.run / trial["folder"] / "memory/instructions.md").write_text("- Add traceToken to logs.\n", encoding="utf-8")
        results = self.report(script=clone / "tests/benchmark.py")
        self.assertFalse(next(row for row in results["trials"] if row["id"] == trial["id"])["behavior_pass"])

    def test_file_checks_require_declared_parameters(self):
        manifest = self.prepare(cases=("explicit_edit", "memory_confirm"))
        for trial in manifest["trials"]:
            folder = self.run / trial["folder"]
            (folder / "response.md").write_text("Synthetic parameter fixture.\n", encoding="utf-8")
        for trial in manifest["trials"]:
            parameters = trial.pop("behavior_parameters")
            with self.subTest(case=trial["case"], condition=trial["condition"]):
                (self.run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                result = self.invoke(REPO / "tests/benchmark.py", "report", self.run, success=False)
                self.assertIn("Missing behavior parameters for trial: " + trial["id"], result.stderr)
            trial["behavior_parameters"] = parameters

    @unittest.skipUnless(os.name == "nt", "Windows export spellings require a Windows run path")
    def test_export_normalizes_windows_case_and_uri_spellings(self):
        self.complete_fixture()
        trial = self.run / "t001"
        spellings = [str(trial).replace(trial.drive, trial.drive.lower()),
                     trial.as_posix().lower(), trial.as_uri().lower()]
        (self.run / "paths.json").write_text(json.dumps(spellings), encoding="utf-8")
        self.export()
        exported = json.loads((self.root / "bundle/paths.json").read_text(encoding="utf-8"))
        self.assertEqual(exported, ["<RUN_DIRECTORY>/t001"] * len(spellings))

    def test_unknown_case_and_existing_output_are_rejected(self):
        result = self.invoke(REPO / "tests/benchmark.py", "prepare", "--output", self.run,
                             "--cases", "not_a_case", success=False)
        self.assertIn("Unknown case", result.stderr)
        self.assertFalse(self.run.exists())
        self.prepare()
        self.invoke(REPO / "tests/benchmark.py", "prepare", "--output", self.run, success=False)

    def test_select_commands_includes_related_scenarios_and_both_conditions(self):
        self.invoke(REPO / "tests/benchmark.py", "prepare", "--output", self.run,
                    "--command", ";;;", "--command", ":::")
        manifest = json.loads((self.run / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["selected_commands"], [";;;", ":::"])
        self.assertEqual(set(manifest["selected_cases"]), {
            "quoted_content", "operator_understanding_correct", "operator_understanding_incorrect",
            "understanding", "hypothesis_restatement",
        })
        self.assertEqual(manifest["planned_trials"], 10)
        for case in manifest["selected_cases"]:
            self.assertEqual({trial["condition"] for trial in manifest["trials"] if trial["case"] == case},
                             {"implicit", "explicit"})
        results = self.report()
        self.assertEqual(results["selected_commands"], [";;;", ":::"])
        self.assertIn("Commands: ;;;, :::", (self.run / "report.md").read_text(encoding="utf-8"))

    def test_command_selection_accepts_aliases_and_rejects_invalid_input(self):
        canonical = self.root / "canonical"
        alias = self.root / "alias"
        self.invoke(REPO / "tests/benchmark.py", "prepare", "--output", canonical, "--command=-->")
        self.invoke(REPO / "tests/benchmark.py", "prepare", "--output", alias, "--command", "rnm")
        first = json.loads((canonical / "manifest.json").read_text(encoding="utf-8"))
        second = json.loads((alias / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(first["selected_commands"], ["-->"])
        self.assertEqual(first["selected_cases"], second["selected_cases"])
        self.assertTrue({"arrow", "arrow_alias", "pagination_discuss", "quoted_content"}
                        <= set(first["selected_cases"]))
        result = self.invoke(REPO / "tests/benchmark.py", "prepare", "--output", self.run,
                             "--command", "unknown", success=False)
        self.assertIn("Unknown command", result.stderr)
        self.assertFalse(self.run.exists())
        result = self.invoke(REPO / "tests/benchmark.py", "prepare", "--output", self.run,
                             "--command", ";;;", "--cases", "help", success=False)
        self.assertIn("not allowed with argument", result.stderr)
        self.assertFalse(self.run.exists())

    def test_memory_writes_require_confirmation(self):
        manifest = self.prepare(cases=("memory", "memory_confirm", "memory_confirm_yes", "memory_skip", "memory_cancel"))
        confirmations = {"memory_confirm", "memory_confirm_yes"}
        original = (REPO / "tests/fixtures/memory/instructions.md").read_bytes()
        for trial in manifest["trials"]:
            folder = self.run / trial["folder"]
            context = (folder / "CONTEXT.md").read_text(encoding="utf-8")
            self.assertEqual("Previous exchange:" in context, trial["case"] != "memory")
            (folder / "response.md").write_text("Unit fixture, not an agent response.\n", encoding="utf-8")
            (folder / "memory/instructions.md").write_bytes(
                original + b"\n- Include a shared requestId in request log entries.\n")
        for row in self.report()["trials"]:
            self.assertEqual(row["behavior_pass"], row["case"] in confirmations)
        for trial in manifest["trials"]:
            if trial["case"] not in confirmations:
                (self.run / trial["folder"] / "memory/instructions.md").write_bytes(original)
        self.assertTrue(all(row["behavior_pass"] for row in self.report()["trials"]))

    def test_discussion_and_followup_file_boundaries(self):
        manifest = self.prepare(cases=("imperative_discussion", "established_task", "explicit_edit",
                                       "agreement_followup", "explicit_followup", "confirm_action", "do_it_followup",
                                       "continue_authorized_work", "discussion_mode_persists",
                                       "discussion_mode_exit", "discussion_mode_reentry", "ambiguous_do_it"))
        allowed = {"explicit_edit", "explicit_followup", "confirm_action", "continue_authorized_work",
                   "discussion_mode_exit", "do_it_followup"}
        for trial in manifest["trials"]:
            folder = self.run / trial["folder"]
            context = (folder / "CONTEXT.md").read_text(encoding="utf-8")
            self.assertEqual("Earlier task context:" in context,
                             trial["case"] in {"established_task", "continue_authorized_work"})
            source = folder / "src/users.js"
            source.write_text(source.read_text(encoding="utf-8").replace("getData", "fetchUsers"),
                              encoding="utf-8", newline="\n")
            (folder / "response.md").write_text("Unit fixture, not an agent response.\n", encoding="utf-8")
        for row in self.report()["trials"]:
            self.assertEqual(row["behavior_pass"], row["case"] in allowed)
        original = (REPO / "tests/fixtures/src/users.js").read_bytes()
        for trial in manifest["trials"]:
            if trial["case"] in {"agreement_followup", "continue_authorized_work",
                                 "discussion_mode_persists", "discussion_mode_exit", "discussion_mode_reentry",
                                 "ambiguous_do_it"}:
                (self.run / trial["folder"] / "src/users.js").write_bytes(original)
        self.assertTrue(all(row["behavior_pass"] for row in self.report()["trials"]
                            if row["case"] in {"agreement_followup", "continue_authorized_work",
                                               "discussion_mode_persists", "discussion_mode_exit", "discussion_mode_reentry",
                                               "ambiguous_do_it"}))

    def test_read_only_input_changes_cannot_pass(self):
        manifest = self.prepare()
        explicit = next(t for t in manifest["trials"] if t["condition"] == "explicit")
        folder = self.run / explicit["folder"]
        (folder / "response.md").write_text("Unit fixture.\n", encoding="utf-8")
        for name in ("CONTEXT.md", "RULES.md", "prompt.txt"):
            with self.subTest(name=name):
                path = folder / name
                original = path.read_bytes()
                path.write_bytes(original + b"Changed input.\n")
                row = self.report()["trials"][0]
                self.assertFalse(row["behavior_pass"])
                self.assertIn(name, row["protected_input_changes"])
                self.assertIsNone(row["full_pass"])
                path.write_bytes(original)

    def test_implicit_rule_creation_is_an_input_change(self):
        manifest = self.prepare()
        implicit = next(t for t in manifest["trials"] if t["condition"] == "implicit")
        folder = self.run / implicit["folder"]
        (folder / "response.md").write_text("Unit fixture.\n", encoding="utf-8")
        (folder / "RULES.md").write_text("Invented rules.\n", encoding="utf-8")
        row = self.report()["trials"][0]
        self.assertFalse(row["behavior_pass"])
        self.assertIn("RULES.md", row["protected_input_changes"])

    def test_unexpected_file_and_deleted_fixture_fail(self):
        manifest = self.prepare()
        folder = self.run / manifest["trials"][0]["folder"]
        (folder / "response.md").write_text("Unit fixture.\n", encoding="utf-8")
        (folder / "extra.txt").write_text("Unexpected.\n", encoding="utf-8")
        (folder / "src/settings.json").unlink()
        row = self.report()["trials"][0]
        self.assertFalse(row["behavior_pass"])
        self.assertIn("extra.txt", row["unexpected_files"])
        self.assertIn("src/settings.json", row["changed_files"])

    def test_crlf_checkout_supports_rename_and_export(self):
        clone = self.clone_harness()
        fixture = clone / "tests/fixtures/src/users.js"
        fixture.write_bytes(fixture.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
        manifest = self.prepare(cases=("explicit_edit",), script=clone / "tests/benchmark.py")
        grades = {}
        for trial in manifest["trials"]:
            folder = self.run / trial["folder"]
            source = folder / "src/users.js"
            source.write_text(source.read_text(encoding="utf-8").replace("getData", "fetchUsers"),
                              encoding="utf-8", newline="\n")
            (folder / "response.md").write_text("Unit fixture.\n", encoding="utf-8")
            grades[trial["id"]] = {"content_pass": True, "note": "Mock grade for CRLF regression"}
        (self.run / "grades.json").write_text(json.dumps(grades), encoding="utf-8")
        results = self.report(script=clone / "tests/benchmark.py")
        self.assertTrue(all(row["behavior_pass"] for row in results["trials"]))
        self.export(script=clone / "tests/export_reference.py")

    def completed_receipt_fixture(self):
        manifest = self.prepare(response_recording="final")
        for trial in manifest["trials"]:
            receipt = {"completion_state": "completed",
                       "raw_final_response": "Unit receipt fixture; not a model response.\n"}
            (self.run / trial["folder"] / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            self.invoke(REPO / "tests/benchmark.py", "grade", self.run, trial["id"], "pass",
                        "--note", "Synthetic fixture for collection regression only")
        return manifest

    def test_completed_receipt_finals_preserve_missing_response_files(self):
        manifest = self.completed_receipt_fixture()
        results = self.report()
        self.assertEqual(len(results["trials"]), 2)
        for row in results["trials"]:
            self.assertTrue(row["content_pass"])
            self.assertTrue(row["behavior_pass"])
            self.assertTrue(row["full_pass"])
            self.assertFalse(row["response_saved"])
            self.assertEqual(row["response_source"], "participant_final")
        self.export()
        for trial in manifest["trials"]:
            for base in (self.run, self.root / "bundle"):
                self.assertFalse((base / trial["folder"] / "response.md").exists())
                self.assertTrue((base / trial["folder"] / "receipt.json").is_file())
        self.assertIn("/receipt.json)", (self.run / "report.md").read_text(encoding="utf-8"))

    def test_legacy_missing_response_file_still_fails_file_check(self):
        manifest = self.completed_receipt_fixture()
        manifest.pop("response_recording")
        (self.run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        for row in self.report()["trials"]:
            self.assertFalse(row["behavior_pass"])
            self.assertFalse(row["full_pass"])
        self.export()

    def test_final_recording_prefers_actual_final_over_response_file(self):
        manifest = self.completed_receipt_fixture()
        trial = manifest["trials"][0]
        folder = self.run / trial["folder"]
        (folder / "response.md").write_text("Different unit fixture.\n", encoding="utf-8")
        row = next(row for row in self.report()["trials"] if row["id"] == trial["id"])
        self.assertEqual(row["response_source"], "participant_final")
        self.assertEqual(row["response"], "Unit receipt fixture; not a model response.\n")
        self.assertTrue(row["behavior_pass"])

    def test_final_recording_requires_a_completed_final(self):
        manifest = self.prepare(response_recording="final")
        folder = self.run / manifest["trials"][0]["folder"]
        (folder / "response.md").write_text("A file alone is not a final.\n", encoding="utf-8")
        self.assertFalse(self.report()["trials"])

    def test_export_rejects_captured_final_changes_after_report(self):
        manifest = self.completed_receipt_fixture()
        self.report()
        path = self.run / manifest["trials"][0]["folder"] / "receipt.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["raw_final_response"] = "Changed synthetic final."
        path.write_text(json.dumps(receipt), encoding="utf-8")
        self.assertIn("Response changed", self.export(success=False).stderr)

    def test_incomplete_receipt_is_not_a_completed_response(self):
        manifest = self.prepare()
        trial = manifest["trials"][0]
        receipt = {"completion_state": "running", "raw_final_response": "Draft unit fixture."}
        (self.run / trial["folder"] / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        self.assertFalse(self.report()["trials"])
        result = self.invoke(REPO / "tests/benchmark.py", "grade", self.run, trial["id"], "pass",
                             "--note", "Synthetic fixture", success=False)
        self.assertIn("no saved answer or captured completed final", result.stderr)
        self.export(success=False)

    def test_export_rejects_escaped_cyrillic_before_creating_bundle(self):
        self.complete_fixture()
        (self.run / "escaped.json").write_text('{"text":"\\u0430"}\n', encoding="utf-8")
        self.assertIn("Non-English Cyrillic", self.export(success=False).stderr)

    def test_export_rejects_response_changes_after_report(self):
        manifest = self.complete_fixture()
        (self.run / manifest["trials"][0]["folder"] / "response.md").write_text("Changed.\n", encoding="utf-8")
        self.assertIn("Response changed", self.export(success=False).stderr)

    def test_export_rejects_input_changes_after_report(self):
        manifest = self.complete_fixture()
        (self.run / manifest["trials"][0]["folder"] / "CONTEXT.md").write_text("Changed.\n", encoding="utf-8")
        self.assertIn("changed after the report", self.export(success=False).stderr)

    def test_export_rejects_duplicate_results(self):
        self.complete_fixture()
        path = self.run / "results.json"
        results = json.loads(path.read_text(encoding="utf-8"))
        results["trials"][1] = results["trials"][0]
        path.write_text(json.dumps(results), encoding="utf-8")
        self.assertIn("Only a completed", self.export(success=False).stderr)

    def test_export_rejects_new_files_after_report(self):
        manifest = self.complete_fixture()
        folder = self.run / manifest["trials"][0]["folder"]
        for name in ("src/new.txt", "memory/new.txt", "extra.txt"):
            with self.subTest(name=name):
                path = folder / name
                path.write_text("Added after reporting.\n", encoding="utf-8")
                self.assertIn("inventory changed", self.export(success=False).stderr)
                path.unlink()


if __name__ == "__main__":
    unittest.main()
