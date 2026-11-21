"""Tests for trace_check.py. Run: python3 -m unittest discover -s scripts -p 'test_*.py'"""

import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import trace_check

VALID = {
    "factory/concept/concept.md": """
# Concept
## Goals
### CON-001: Users can add numbers
""",
    "factory/requirements/requirements.md": """
### UC-001: Add numbers
- **Source:** CON-001
- **Primary actor:** User

### US-001: Quick sums
- **Source:** UC-001
- **Story:** As a user, I want to add two numbers, so that I get the total quickly.

### REQ-001: Add two integers
- **Source:** UC-001, US-001
- **EARS:** event-driven
- **Statement:** When the user enters two integers, the system shall print their sum.

### SCN-001: Add numbers from the CLI
- **Covers:** UC-001, REQ-001
""",
    "factory/architecture/architecture.md": """
```mermaid
flowchart LR
  ARCH-999 --> ARCH-998
```
### EXT-001: User
### ARCH-001: CLI
- **Satisfies:** REQ-001
### ARCH-002: Calculator
- **Satisfies:** REQ-001
### IF-001: Calculator API
- **Between:** ARCH-001, ARCH-002
### IF-002: Command line
- **Between:** EXT-001, ARCH-001
- **Satisfies:** REQ-001
""",
    "factory/design/ARCH-001-cli.md": """
### DES-001: Argument parser
- **Refines:** ARCH-001, IF-002
- **Source location:** `src/cli.py`
""",
    "factory/design/ARCH-002-calculator.md": """
### DES-002: add()
- **Refines:** ARCH-002, IF-001
""",
    "src/cli.py": "# @implements DES-001\ndef main(): ...\n",
    "src/calc.py": "# @implements DES-002\ndef add(a, b): return a + b\n",
    "src/__init__.py": "",
    "factory/verification/unit/specs.md": """
### UT-001: parses two ints
- **Verifies:** DES-001
### UT-002: adds
- **Verifies:** DES-002
""",
    "factory/verification/integration/integration-tests.md": """
### IT-001: CLI calls calculator
- **Verifies:** IF-001, DES-001, DES-002
""",
    "factory/verification/system/system-tests.md": """
### ST-001: prints sum end to end
- **Verifies:** SCN-001, ARCH-001, ARCH-002, IF-002
""",
    "factory/acceptance/acceptance-tests.md": """
### AT-001: sum of two integers is printed
- **Verifies:** REQ-001
""",
    "factory/acceptance/acceptance-report.md": """
| Item | Verdict | Evidence | Notes |
|---|---|---|---|
| CON-001 | accepted | AT-001 | |
| REQ-001 | accepted | AT-001, ST-001 | AC1 ok |
""",
    "tests/unit/test_units.py": "# @test UT-001\n# @test UT-002\n",
    "tests/integration/test_int.py": "# @test IT-001\n",
    "tests/system/test_sys.py": "# @test ST-001\n",
    "tests/acceptance/test_acc.py": "# @test AT-001\n",
}

REQS = "factory/requirements/requirements.md"


class TraceCheckTest(unittest.TestCase):
    def build(self, files: dict) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for rel, content in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        return root

    def run_check(self, files: dict, *args: str) -> tuple[int, dict]:
        root = self.build(files)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = trace_check.main(["--root", str(root), "--json", *args])
        return code, json.loads(buf.getvalue())

    def messages(self, result: dict, key: str = "errors") -> str:
        return "\n".join(i["message"] for i in result[key])

    def changed(self, path: str, old: str, new: str) -> dict:
        files = dict(VALID)
        self.assertIn(old, files[path])
        files[path] = files[path].replace(old, new)
        return files

    # ------------------------------------------------------------------ whole-model behavior

    def test_valid_project_passes_acceptance_and_writes_matrix(self):
        root = self.build(VALID)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = trace_check.main(["--root", str(root)])
        self.assertEqual(code, 0, buf.getvalue())
        matrix = (root / "factory/trace/matrix.md").read_text()
        self.assertIn("| REQ-001 | event-driven | UC-001, US-001 | SCN-001 | ARCH-001, ARCH-002, IF-002 | AT-001 | accepted |",
                      matrix)
        self.assertIn("| UC-001 | CON-001 | US-001 | REQ-001 | SCN-001 |", matrix)
        self.assertIn("| ARCH-001 | REQ-001 | IF-001, IF-002 | DES-001 | ST-001 |", matrix)
        self.assertIn("| DES-002 | ARCH-002, IF-001 | IT-001 | src/calc.py | UT-002 |", matrix)
        self.assertIn("PASS", matrix)

    def test_historical_memory_cannot_redefine_live_artifacts_or_verdicts(self):
        files = dict(VALID)
        files['factory/memory.md'] = """
# Project memory
### CON-999: An old idea, not current scope
### REQ-001: Earlier wording, retained as history only
- **Source:** CON-999
- **Statement:** Old behavior without a valid EARS statement.
| REQ-001 | rejected | AT-999 | Historical result, not a current verdict |
"""
        code, result = self.run_check(files)
        self.assertEqual(code, 0, self.messages(result))
        self.assertEqual(result['counts']['CON'], 1)
        self.assertEqual(result['counts']['REQ'], 1)
        self.assertEqual(result['counts']['AT'], 1)

    def test_gates_follow_the_eight_v_model_stages(self):
        self.assertEqual(trace_check.GATES, ["requirements", "architecture", "design", "implementation",
                                             "unit", "integration", "system", "acceptance"])

    def test_empty_project_fails_requirements_gate(self):
        code, result = self.run_check({}, "--gate", "requirements")
        self.assertEqual(code, 1)
        self.assertIn("No CON items", self.messages(result))

    def test_later_stage_gaps_are_warnings_at_earlier_gates(self):
        files = dict(VALID)
        files.pop("factory/verification/unit/specs.md")
        code, result = self.run_check(files, "--gate", "implementation")
        self.assertEqual(code, 0)
        self.assertIn("DES-001 is not verified by any UT", self.messages(result, "warnings"))
        code, result = self.run_check(files, "--gate", "unit")
        self.assertEqual(code, 1)
        self.assertIn("DES-001 is not verified by any UT", self.messages(result))

    def test_ids_in_code_fences_and_comments_are_ignored(self):
        files = dict(VALID)
        files["factory/concept/concept.md"] += "<!--\n### CON-777: commented out\n-->\n"
        code, result = self.run_check(files, "--gate", "acceptance")
        self.assertEqual(code, 0, self.messages(result))
        self.assertEqual(result["counts"]["ARCH"], 2)
        self.assertEqual(result["counts"]["CON"], 1)

    def test_dangling_and_wrong_type_links(self):
        files = dict(VALID)
        files["factory/verification/unit/specs.md"] = """
### UT-001: parses
- **Verifies:** DES-001, DES-099
### UT-002: wrong level
- **Verifies:** REQ-001
"""
        code, result = self.run_check(files, "--gate", "unit")
        msgs = self.messages(result)
        self.assertEqual(code, 1)
        self.assertIn("UT-001 Verifies DES-099, which is not defined", msgs)
        self.assertIn("Verifies may only target ['DES']", msgs)

    def test_duplicates_wrong_location_and_retired(self):
        files = dict(VALID)
        files["factory/design/ARCH-002-calculator.md"] += "### DES-001: duplicate\n- **Refines:** ARCH-002\n"
        files["factory/design/misplaced.md"] = "### REQ-050: in design dir\n- **Source:** CON-001\n"
        files[REQS] = files[REQS].replace(
            "### SCN-001: Add numbers from the CLI",
            "### REQ-003 (retired): old\n- **Source:** CON-001\n"
            "### SCN-002: old flow\n- **Covers:** REQ-003\n"
            "### SCN-001: Add numbers from the CLI",
        )
        _, result = self.run_check(files, "--gate", "requirements")
        msgs = self.messages(result)
        self.assertIn("Duplicate definition of DES-001", self.messages(result, "warnings"))
        self.assertIn("REQ-050 must be defined under factory/requirements/", msgs)
        self.assertIn("SCN-002 traces only to retired items", msgs)

    # ------------------------------------------------------------------ requirements

    def test_unallocated_requirement_and_uncovered_concept(self):
        files = dict(VALID)
        files["factory/concept/concept.md"] += "### CON-002: Orphan goal\n"
        files[REQS] += "### REQ-002: Unallocated\n- **Source:** CON-001\n"
        _, result = self.run_check(files, "--gate", "architecture")
        msgs = self.messages(result)
        self.assertIn("CON-002 is not covered by any REQ", msgs)
        self.assertIn("REQ-002 is not allocated to any ARCH/IF", msgs)

    def test_use_case_must_be_refined_and_covered_by_scenario(self):
        files = dict(VALID)
        files[REQS] += "### UC-002: Unrefined\n- **Source:** CON-001\n"
        code, result = self.run_check(files, "--gate", "requirements")
        msgs = self.messages(result)
        self.assertEqual(code, 1)
        self.assertIn("UC-002 is not refined into any REQ", msgs)
        self.assertIn("UC-002 is not covered by any SCN", msgs)

    def test_user_story_must_be_refined_and_sourced(self):
        files = dict(VALID)
        files[REQS] += "### US-002: Orphan story\n"
        _, result = self.run_check(files, "--gate", "requirements")
        msgs = self.messages(result)
        self.assertIn("US-002 has no 'Source' link", msgs)
        self.assertIn("US-002 is not refined into any REQ", msgs)

    def test_coverage_is_transitive_through_use_case_and_story(self):
        files = self.changed(REQS, "- **Source:** UC-001, US-001", "- **Source:** US-001")
        code, result = self.run_check(files, "--gate", "requirements")
        self.assertEqual(code, 0, self.messages(result))

        files[REQS] = VALID[REQS].replace("- **Source:** UC-001, US-001", "- **Source:** CON-001").replace(
            "- **Source:** UC-001\n- **Story", "- **Source:** CON-001\n- **Story"
        )
        code, result = self.run_check(files, "--gate", "requirements")
        self.assertEqual(code, 1)
        self.assertIn("UC-001 is not refined into any REQ", self.messages(result))

    def test_scenario_must_cover_a_requirement(self):
        files = self.changed(REQS, "- **Covers:** UC-001, REQ-001", "- **Covers:** UC-001")
        _, result = self.run_check(files, "--gate", "requirements")
        self.assertIn("SCN-001 has no 'Covers' link (at least one ['REQ'])", self.messages(result))

    def test_ears_requirement_checks(self):
        files = dict(VALID)
        files[REQS] += """
### REQ-010: No statement
- **Source:** UC-001
### REQ-011: Not EARS
- **Source:** UC-001
- **EARS:** ubiquitous
- **Statement:** Users can export reports quickly.
### REQ-012: Wrong declared pattern
- **Source:** UC-001
- **EARS:** event-driven
- **Statement:** While offline, the app shall queue edits.
### REQ-013: Missing declared pattern
- **Source:** UC-001
- **Statement:** The app shall store data locally.
### REQ-014: Not atomic
- **Source:** UC-001
- **EARS:** ubiquitous
- **Statement:** The app shall log in and the app shall sync.
"""
        _, result = self.run_check(files, "--gate", "requirements")
        msgs = self.messages(result)
        self.assertIn("REQ-010 has no 'Statement' (EARS)", msgs)
        self.assertIn("REQ-011 Statement is not valid EARS: must contain exactly one 'shall' (found 0)", msgs)
        self.assertIn("REQ-012 declares EARS 'event-driven' but the statement reads as 'state-driven'", msgs)
        self.assertIn("REQ-013 needs an 'EARS' field", msgs)
        self.assertIn("REQ-014 Statement is not valid EARS: must contain exactly one 'shall' (found 2)", msgs)

    def test_ears_pattern_classification(self):
        cases = {
            "The system shall encrypt stored passwords.": "ubiquitous",
            "When the user submits a form with name, email, and age, the system shall validate all fields.":
                "event-driven",
            "While the device is offline, the app shall queue outgoing messages.": "state-driven",
            "If the payment provider times out, then the system shall cancel the order.": "unwanted",
            "Where dark mode is enabled, the UI shall use the dark palette.": "optional",
            "While in edit mode, when the user presses Escape, the editor shall discard changes.": "complex",
            "While a session is active, if the token expires, then the server shall reject requests.": "complex",
            "The CLI shall not write outside the working directory.": "ubiquitous",
            "**When the timer elapses, the system shall sound an alarm.**": "event-driven",
        }
        for statement, expected in cases.items():
            with self.subTest(statement=statement):
                self.assertEqual(trace_check.ears_pattern(statement), (expected, None))

    def test_ears_pattern_rejections(self):
        cases = {
            "If the disk is full, the system shall warn the user.": "need ', then the <system> shall",
            "System shall start.": "does not match EARS",
            "When clicked the button shall glow.": "does not match EARS",
            "The system should respond.": "exactly one 'shall' (found 0)",
            "When X, the system shall A and shall B.": "exactly one 'shall' (found 2)",
        }
        for statement, fragment in cases.items():
            with self.subTest(statement=statement):
                pattern, problem = trace_check.ears_pattern(statement)
                self.assertIsNone(pattern)
                self.assertIn(fragment, problem)

    # ------------------------------------------------------------------ architecture, design, implementation

    def test_interface_needs_an_arch_endpoint(self):
        files = self.changed("factory/architecture/architecture.md",
                             "- **Between:** ARCH-001, ARCH-002", "- **Between:** EXT-001")
        _, result = self.run_check(files, "--gate", "architecture")
        self.assertIn("IF-001 has no 'Between' link (at least one ['ARCH'])", self.messages(result))

    def test_orphan_source_file_and_exemption(self):
        files = dict(VALID, **{"src/extra.py": "print('hi')\n"})
        code, result = self.run_check(files, "--gate", "implementation")
        self.assertEqual(code, 1)
        self.assertIn("no @implements tag", self.messages(result))
        files["src/extra.py"] = "# @trace-exempt generated\nprint('hi')\n"
        code, _ = self.run_check(files, "--gate", "implementation")
        self.assertEqual(code, 0)

    def test_implements_must_target_existing_des(self):
        files = dict(VALID, **{"src/calc.py": "# @implements DES-002, ARCH-001, DES-404\n"})
        _, result = self.run_check(files, "--gate", "implementation")
        msgs = self.messages(result)
        self.assertIn("@implements ARCH-001: code must implement DES items", msgs)
        self.assertIn("@implements DES-404 references an undefined item", msgs)

    # ------------------------------------------------------------------ right side of the V

    def test_test_tags_location_and_resolution(self):
        files = dict(VALID)
        files["tests/system/test_sys.py"] = "# @test ST-001\n# @test UT-001\n# @test ST-777\n"
        _, result = self.run_check(files, "--gate", "system")
        msgs = self.messages(result)
        self.assertIn("@test UT-001 must live under tests/unit/", msgs)
        self.assertIn("@test ST-777 references an undefined test case", msgs)

    def test_test_case_without_automation(self):
        files = dict(VALID, **{"tests/integration/test_int.py": "# no tags\n"})
        _, result = self.run_check(files, "--gate", "integration")
        self.assertIn("IT-001 has no automated test", self.messages(result))

    def test_integration_testing_verifies_design(self):
        files = dict(VALID)
        files["factory/design/ARCH-001-cli.md"] += "### DES-003: Output formatter\n- **Refines:** ARCH-001\n"
        files["src/fmt.py"] = "# @implements DES-003\n"
        files["factory/verification/unit/specs.md"] += "### UT-003: formats\n- **Verifies:** DES-003\n"
        files["tests/unit/test_units.py"] += "# @test UT-003\n"
        files["factory/verification/integration/integration-tests.md"] = (
            "### IT-001: calculator alone\n- **Verifies:** DES-002\n"
        )
        code, result = self.run_check(files, "--gate", "integration")
        msgs = self.messages(result)
        self.assertEqual(code, 1)
        self.assertIn("IF-001 (internal interface) is not verified by any IT", msgs)
        self.assertIn("ARCH-001 has 2 design units but no IT verifies their collaboration", msgs)
        self.assertNotIn("ARCH-002 has", msgs)
        self.assertNotIn("IF-002", msgs)

    def test_system_testing_verifies_architecture(self):
        files = self.changed("factory/verification/system/system-tests.md",
                             "- **Verifies:** SCN-001, ARCH-001, ARCH-002, IF-002", "- **Verifies:** ARCH-001")
        code, result = self.run_check(files, "--gate", "system")
        msgs = self.messages(result)
        self.assertEqual(code, 1)
        self.assertIn("ARCH-002 is not exercised by any ST", msgs)
        self.assertIn("IF-002 (external interface) is not verified by any ST", msgs)
        self.assertIn("SCN-001 is not verified end to end by any ST", msgs)
        self.assertNotIn("IF-001", msgs)

    def test_system_tests_may_not_verify_requirements_directly(self):
        files = self.changed("factory/verification/system/system-tests.md",
                             "- **Verifies:** SCN-001,", "- **Verifies:** REQ-001, SCN-001,")
        _, result = self.run_check(files, "--gate", "system")
        self.assertIn("Verifies may only target ['ARCH', 'IF', 'SCN']", self.messages(result))

    def test_acceptance_verifies_every_requirement(self):
        files = dict(VALID)
        files[REQS] += ("### REQ-002: Subtract\n- **Source:** UC-001\n- **EARS:** event-driven\n"
                        "- **Statement:** When the user enters two integers with '-', the system shall print their difference.\n")
        files["factory/architecture/architecture.md"] = files["factory/architecture/architecture.md"].replace(
            "### ARCH-002: Calculator\n- **Satisfies:** REQ-001", "### ARCH-002: Calculator\n- **Satisfies:** REQ-001, REQ-002"
        )
        code, result = self.run_check(files, "--gate", "acceptance")
        msgs = self.messages(result)
        self.assertEqual(code, 1)
        self.assertIn("REQ-002 is not verified by any AT", msgs)
        self.assertIn("REQ-002 has no verdict in the acceptance report", msgs)

    def test_rejected_verdict_fails_acceptance(self):
        files = self.changed("factory/acceptance/acceptance-report.md",
                             "| REQ-001 | accepted | AT-001, ST-001 |", "| REQ-001 | rejected | AT-001 |")
        code, result = self.run_check(files, "--gate", "acceptance")
        self.assertEqual(code, 1)
        self.assertIn("REQ-001 is not accepted", self.messages(result))

    def test_verdict_evidence_rules(self):
        files = self.changed("factory/acceptance/acceptance-report.md",
                             "| REQ-001 | accepted | AT-001, ST-001 | AC1 ok |", "| REQ-001 | accepted | | |")
        _, result = self.run_check(files, "--gate", "acceptance")
        self.assertIn("REQ-001 verdict cites no evidence", self.messages(result))

        files = self.changed("factory/acceptance/acceptance-report.md",
                             "| REQ-001 | accepted | AT-001, ST-001 | AC1 ok |", "| REQ-001 | waived | | Q-004 |")
        code, result = self.run_check(files, "--gate", "acceptance")
        self.assertEqual(code, 0, self.messages(result))

        files = dict(VALID)
        files["factory/acceptance/acceptance-report.md"] += "| REQ-404 | accepted | AT-999 | |\n| CON-001 | maybe | | |\n"
        _, result = self.run_check(files, "--gate", "acceptance")
        msgs = self.messages(result)
        self.assertIn("Verdict for REQ-404, which is not defined", msgs)
        self.assertIn("cites AT-999, which is not defined", msgs)
        self.assertIn("must be accepted|rejected|waived, not 'maybe'", msgs)

    # ------------------------------------------------------------------ impact

    def test_impact_walks_downstream_to_code_and_tests(self):
        code, result = self.run_check(VALID, "--impact", "ARCH-002")
        self.assertEqual(code, 0)
        impact = result["impact"]
        self.assertEqual(impact["IF"], ["IF-001"])
        self.assertEqual(impact["DES"], ["DES-002"])
        self.assertEqual(impact["ST"], ["ST-001"])
        self.assertIn("IT-001", impact["IT"])
        self.assertIn("src/calc.py", impact["code"])
        self.assertIn("tests/unit/test_units.py", impact["tests"])
        self.assertNotIn("REQ", impact)

    def test_impact_of_requirement_reaches_acceptance_tests(self):
        _, result = self.run_check(VALID, "--impact", "REQ-001")
        impact = result["impact"]
        self.assertEqual(impact["AT"], ["AT-001"])
        self.assertIn("ARCH-002", impact["ARCH"])
        self.assertIn("tests/acceptance/test_acc.py", impact["tests"])

    def test_impact_unknown_id(self):
        code, result = self.run_check(VALID, "--impact", "REQ-404")
        self.assertEqual(code, 1)
        self.assertEqual(result["unknown"], ["REQ-404"])

    # --------------------------------------------------------- specification vs execution

    def test_each_test_level_can_specify_before_code_or_automation_exists(self):
        files = {p: v for p, v in VALID.items() if not p.startswith(("src/", "tests/"))
                 and not p.endswith("acceptance-report.md")}
        for gate in ("unit", "integration", "system", "acceptance"):
            with self.subTest(gate=gate):
                code, result = self.run_check(files, "--gate", gate, "--phase", "specify")
                self.assertEqual(code, 0, self.messages(result))
                self.assertEqual(result["phase"], "specify")
        code, result = self.run_check(files, "--gate", "unit")
        self.assertEqual(code, 1)
        self.assertIn("no implementing code", self.messages(result))
        self.assertIn("no automated test", self.messages(result))

    def test_acceptance_spec_needs_only_requirements_and_does_not_write_matrix(self):
        files = {p: v for p, v in VALID.items() if p.startswith(("factory/concept/", "factory/requirements/"))
                 or p == "factory/acceptance/acceptance-tests.md"}
        root = self.build(files)
        with redirect_stdout(io.StringIO()):
            code = trace_check.main(["--root", str(root), "--gate", "acceptance", "--phase", "specify"])
        self.assertEqual(code, 0)
        self.assertFalse((root / "factory/trace/matrix.md").exists())

    def test_specification_checks_still_require_cases_and_valid_oracles(self):
        files = self.changed("factory/verification/unit/specs.md", "- **Verifies:** DES-002", "- **Verifies:** REQ-001")
        code, result = self.run_check(files, "--gate", "unit", "--phase", "specify")
        self.assertEqual(code, 1)
        self.assertIn("Verifies may only target", self.messages(result))
        self.assertIn("DES-002 is not verified by any UT", self.messages(result))
        files = dict(VALID)
        files.pop("factory/verification/integration/integration-tests.md")
        code, _ = self.run_check(files, "--gate", "integration", "--phase", "specify")
        self.assertEqual(code, 1)

    def test_component_checks_allow_pending_siblings_but_global_gate_fails(self):
        files = {p: v for p, v in VALID.items() if p not in {
            "factory/design/ARCH-002-calculator.md", "src/calc.py", "factory/verification/unit/specs.md"}}
        files["factory/verification/unit/specs.md"] = "### UT-001: parser\n- **Verifies:** DES-001\n"
        files["tests/unit/test_units.py"] = "# @test UT-001\n"
        for gate in ("design", "implementation", "unit"):
            with self.subTest(gate=gate):
                code, result = self.run_check(files, "--gate", gate, "--scope", "ARCH-001")
                self.assertEqual(code, 0, self.messages(result))
                self.assertEqual(result["check"], "component")
                self.assertIn("ARCH-002 is not refined", self.messages(result, "warnings"))
                code, _ = self.run_check(files, "--gate", gate)
                self.assertEqual(code, 1)

    def test_scope_does_not_hide_selected_component_or_upstream_gaps(self):
        files = dict(VALID)
        files.pop("src/cli.py")
        code, result = self.run_check(files, "--gate", "implementation", "--scope", "ARCH-001")
        self.assertEqual(code, 1)
        self.assertIn("DES-001 has no implementing code", self.messages(result))
        files = dict(VALID)
        files[REQS] += "\n### REQ-002: Store\n- **Source:** CON-001\n- **EARS:** ubiquitous\n- **Statement:** The system shall store results.\n"
        code, result = self.run_check(files, "--gate", "design", "--scope", "ARCH-001")
        self.assertEqual(code, 1)
        self.assertIn("REQ-002 is not allocated", self.messages(result))

    def test_scope_does_not_hide_duplicates_bad_tags_or_orphan_source(self):
        files = dict(VALID)
        files["factory/design/duplicate.md"] = "### DES-002: Duplicate\n- **Refines:** ARCH-002\n"
        files["src/other.py"] = "print('untraced')\n"
        files["tests/unit/test_units.py"] += "# @test UT-999\n"
        code, result = self.run_check(files, "--gate", "unit", "--scope", "ARCH-001")
        self.assertEqual(code, 1)
        msgs = self.messages(result)
        self.assertIn("Duplicate definition", msgs)
        self.assertIn("Source file has no", msgs)
        self.assertIn("undefined test case", msgs)

    def test_invalid_scope_phase_and_matrix_combinations_are_rejected(self):
        root = self.build(VALID)
        from contextlib import redirect_stderr
        for args in (("--gate", "design", "--phase", "specify"),
                     ("--gate", "unit", "--scope", "ARCH-999"),
                     ("--gate", "acceptance", "--scope", "ARCH-001"),
                     ("--gate", "unit", "--scope", "ARCH-001", "--matrix"),
                     ("--gate", "acceptance", "--phase", "specify", "--matrix")):
            with self.subTest(args=args), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                trace_check.main(["--root", str(root), *args])
            self.assertEqual(error.exception.code, 2)

    # ---------------------------------------------------------- dependencies and regression

    def test_dependency_impact_reaches_callers_code_and_their_tests(self):
        files = dict(VALID)
        files["factory/design/ARCH-001-cli.md"] += "\n- **Dependencies:** DES-002\n"
        files.pop("tests/unit/test_units.py")
        files["tests/unit/test_cli.py"] = "# @test UT-001\n"
        files["tests/unit/test_calc.py"] = "# @test UT-002\n"
        code, result = self.run_check(files, "--impact", "DES-002")
        self.assertEqual(code, 0)
        self.assertEqual(result["impact"]["DES"], ["DES-001"])
        self.assertIn("src/cli.py", result["impact"]["code"])
        self.assertIn("tests/unit/test_cli.py", result["impact"]["tests"])
        self.assertEqual(result["minimum_suite"], "slow")
        self.assertIn("ST-001", result["regression"]["ST"])
        self.assertIn("AT-001", result["regression"]["AT"])
        self.assertNotIn("ARCH", result["impact"])
        self.assertNotIn("AT", result["impact"])

    def test_private_unit_impact_keeps_higher_verification_separate(self):
        _, result = self.run_check(VALID, "--impact", "DES-002")
        self.assertEqual(result["minimum_suite"], "fast")
        self.assertNotIn("ST", result["impact"])
        self.assertIn("tests/system/test_sys.py", result["regression"]["tests"])
        self.assertIn("tests/acceptance/test_acc.py", result["regression"]["tests"])

    def test_provider_impact_reaches_callers_via_realized_interface(self):
        files = dict(VALID)
        files['factory/design/ARCH-001-cli.md'] += '\n- **Dependencies:** IF-001\n'
        code, result = self.run_check(files, '--impact', 'DES-002')
        self.assertEqual(code, 0)
        self.assertIn('DES-001', result['impact']['DES'])
        self.assertIn('src/cli.py', result['impact']['code'])
        self.assertNotIn('IF', result['impact'])
        self.assertEqual(result['minimum_suite'], 'slow')

    def test_dependencies_are_validated_without_becoming_refinement(self):
        for target in ("DES-999", "REQ-001", "DES-002", "BOGUS-001"):
            files = dict(VALID)
            files["factory/design/ARCH-002-calculator.md"] += f"\n- **Dependencies:** {target}\n"
            code, result = self.run_check(files, "--gate", "design")
            self.assertEqual(code, 1, target)
            self.assertIn("Dependencies", self.messages(result))
        files = dict(VALID)
        files["factory/design/ARCH-002-calculator.md"] += "\n- **Dependencies:** DES-001\n"
        root = self.build(files)
        self.assertNotIn(("DES-002", "Dependencies"), trace_check.load(root).children().get("DES-001", []))
        code, result = self.run_check(files, "--gate", "acceptance")
        self.assertEqual(code, 0, self.messages(result))

    def test_retired_dependencies_fail_and_matrix_includes_callers(self):
        files = dict(VALID)
        files['factory/design/ARCH-001-cli.md'] += '\n- **Dependencies:** DES-002\n'
        root = self.build(files)
        model = trace_check.load(root)
        report = trace_check.matrix(model, trace_check.check(model), 'acceptance')
        self.assertIn('| DES-002 | — | DES-001 |', report)
        self.assertIn('| DES-001 | DES-002 | — |', report)
        files['factory/design/ARCH-002-calculator.md'] = files['factory/design/ARCH-002-calculator.md'].replace(
            '### DES-002: add()', '### DES-002 (retired): add()')
        _, result = self.run_check(files, '--gate', 'design')
        self.assertIn('dependency must be live', self.messages(result))

    def test_dependency_cycles_terminate_and_unknown_component_impact_is_reported(self):
        files = dict(VALID)
        files["factory/design/ARCH-001-cli.md"] += "\n- **Dependencies:** DES-002\n"
        files["factory/design/ARCH-002-calculator.md"] += "\n- **Dependencies:** DES-001\n"
        code, result = self.run_check(files, "--impact", "DES-002")
        self.assertEqual(code, 0)
        self.assertIn("DES-001", result["impact"]["DES"])
        code, result = self.run_check(VALID, "--impact", "ARCH-999")
        self.assertEqual(code, 1)
        self.assertEqual(result["unknown"], ["ARCH-999"])

    # ---------------------------------------------------------- acceptance evidence

    def test_notes_cannot_fill_an_empty_evidence_cell(self):
        files = self.changed("factory/acceptance/acceptance-report.md",
                             "| REQ-001 | accepted | AT-001, ST-001 | AC1 ok |",
                             "| REQ-001 | accepted | | REQ-001 reviewed; AT-001 mentioned |")
        code, result = self.run_check(files)
        self.assertEqual(code, 1)
        self.assertIn("verdict cites no evidence", self.messages(result))

    def test_evidence_must_be_live_relevant_tests_in_the_evidence_cell(self):
        for evidence in ("REQ-001", "BOGUS-001", "ST-001"):
            files = self.changed("factory/acceptance/acceptance-report.md",
                                 "| REQ-001 | accepted | AT-001, ST-001 | AC1 ok |",
                                 f"| REQ-001 | accepted | {evidence} | AT-001 in notes |")
            code, _ = self.run_check(files)
            self.assertEqual(code, 1, evidence)
        files = dict(VALID)
        files["factory/acceptance/acceptance-report.md"] += "| CON-001 | accepted | AT-001 | duplicate |\n"
        code, result = self.run_check(files)
        self.assertEqual(code, 1)
        self.assertIn("Duplicate verdict", self.messages(result))

    def test_unrelated_or_retired_evidence_and_retired_test_tags_fail(self):
        files = dict(VALID)
        files['factory/concept/concept.md'] += '\n### CON-002: Other goal\n'
        files[REQS] += '\n### REQ-002: Other\n- **Source:** CON-002\n- **EARS:** ubiquitous\n- **Statement:** The system shall store results.\n'
        files['factory/acceptance/acceptance-report.md'] += '| REQ-002 | accepted | AT-001 | |\n'
        _, result = self.run_check(files)
        self.assertIn('unrelated evidence AT-001', self.messages(result))
        files = dict(VALID)
        files['factory/verification/unit/specs.md'] += '\n### UT-999 (retired): Old\n- **Verifies:** DES-002\n'
        files['tests/unit/test_units.py'] += '# @test UT-999\n'
        files['factory/acceptance/acceptance-report.md'] = files['factory/acceptance/acceptance-report.md'].replace('AT-001, ST-001', 'AT-001, UT-999')
        _, result = self.run_check(files)
        self.assertIn('references a retired test case', self.messages(result))
        self.assertIn('must be a live UT/IT/ST/AT case', self.messages(result))

    # ---------------------------------------------------------- actual Git baseline integrity

    def git(self, root, *args):
        return subprocess.run(['git', '-c', 'user.name=Factory test', '-c', 'user.email=factory@example.invalid',
                               '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                               '-C', str(root), *args], check=True, capture_output=True, text=True).stdout.strip()

    def baseline_repo(self):
        root = self.build(VALID)
        self.git(root, 'init')
        self.git(root, 'add', '.')
        self.git(root, 'commit', '-m', 'chore: baseline fixture')
        return root, self.git(root, 'rev-parse', 'HEAD')

    def test_baseline_detects_untagged_behavior_change_that_trace_check_cannot(self):
        root, ref = self.baseline_repo()
        self.assertTrue(trace_check.baseline_changes(root, ref, ['src'])['pass'])
        (root / 'src/calc.py').write_text('# @implements DES-002\ndef add(a, b): return a - b\n')
        self.assertFalse(trace_check.check(trace_check.load(root)))
        result = trace_check.baseline_changes(root, ref, ['src'])
        self.assertFalse(result['pass'])
        self.assertEqual(result['changed'], ['src/calc.py'])
        self.git(root, 'add', 'src/calc.py')
        self.git(root, 'commit', '-m', 'fix: out-of-band change')
        self.assertEqual(trace_check.baseline_changes(root, ref, ['src'])['changed'], ['src/calc.py'])

    def test_baseline_includes_staged_deleted_untracked_and_renamed_files(self):
        root, ref = self.baseline_repo()
        self.git(root, 'mv', 'src/calc.py', 'src/calculator with spaces.py')
        (root / 'src/cli.py').unlink()
        (root / 'src/new.py').write_text('# @implements DES-001\n')
        (root / 'outside.txt').write_text('outside the owned paths')
        before = self.git(root, 'status', '--porcelain')
        result = trace_check.baseline_changes(root, ref, ['src'])
        self.assertEqual(result['changed'], ['src/calc.py', 'src/calculator with spaces.py', 'src/cli.py', 'src/new.py'])
        self.assertEqual(before, self.git(root, 'status', '--porcelain'))

    def test_baseline_detects_index_change_even_when_worktree_matches_baseline(self):
        root, ref = self.baseline_repo()
        p = root / 'src/calc.py'
        p.write_text('# @implements DES-002\ndef add(a, b): return a - b\n')
        self.git(root, 'add', 'src/calc.py')
        p.write_text(VALID['src/calc.py'])
        before = self.git(root, 'status', '--porcelain')
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = trace_check.main(['--root', str(root), '--baseline', ref, '--paths', 'src', '--json'])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(buf.getvalue())['changed'], ['src/calc.py'])
        self.assertEqual(before, self.git(root, 'status', '--porcelain'))

    def test_baseline_cli_success_is_read_only_and_honors_literal_paths(self):
        root, ref = self.baseline_repo()
        (root / 'src/new.py').write_text('# @implements DES-001\n')
        before = self.git(root, 'status', '--porcelain')
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = trace_check.main(['--root', str(root), '--baseline', ref, '--paths', 'src/calc.py', '--json'])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(buf.getvalue())['pass'])
        self.assertFalse((root / 'factory/trace/matrix.md').exists())
        self.assertEqual(before, self.git(root, 'status', '--porcelain'))

    def test_baseline_cli_fails_closed_for_bad_ref_or_paths(self):
        root, _ = self.baseline_repo()
        for args in (['--baseline', 'missing', '--paths', 'src'],
                     ['--baseline', 'HEAD'], ['--baseline', 'HEAD', '--paths', '../src'],
                     ['--baseline', 'HEAD', '--paths', 'typo-does-not-exist'],
                     ['--baseline', 'HEAD', '--paths', ':(exclude)src']):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = trace_check.main(['--root', str(root), '--json', *args])
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(buf.getvalue())['pass'])


if __name__ == "__main__":
    unittest.main()
