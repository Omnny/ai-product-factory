"""Tests for trace_check.py. Run: python3 -m unittest discover -s scripts -p 'test_*.py'"""

import io
import json
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


if __name__ == "__main__":
    unittest.main()
