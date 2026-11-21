#!/usr/bin/env python3
"""V-model traceability checker for the AI Product Factory.

Builds the trace graph from inline IDs in factory artifacts, `@implements` tags in
src/, and `@test` tags in tests/, then enforces the rules in docs/traceability.md.

Usage:
  trace_check.py --gate <stage>            check rules up to <stage> (later stages -> warnings)
                                           stages: requirements architecture design implementation
                                                   unit integration system acceptance
  trace_check.py --impact ID [ID ...]      list everything downstream of the given IDs
  trace_check.py --gate acceptance --matrix factory/trace/matrix.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# The eight V-model stages, in V order: left side top-down, then right side bottom-up.
# Pairs: requirements <-> acceptance, architecture <-> system, design <-> integration, implementation <-> unit.
GATES = ["requirements", "architecture", "design", "implementation", "unit", "integration", "system", "acceptance"]

# prefix -> (stage, directory under factory/, {link field: allowed target prefixes})
# CON items live in the concept (the factory's input) and are checked with the requirements stage.
TYPES: dict[str, tuple[str, str, dict[str, set[str]]]] = {
    "CON": ("requirements", "concept", {}),
    "UC": ("requirements", "requirements", {"Source": {"CON"}}),
    "US": ("requirements", "requirements", {"Source": {"CON", "UC"}}),
    "REQ": ("requirements", "requirements", {"Source": {"CON", "UC", "US"}}),
    "SCN": ("requirements", "requirements", {"Covers": {"REQ", "UC"}}),
    "EXT": ("architecture", "architecture", {}),
    "ARCH": ("architecture", "architecture", {"Satisfies": {"REQ"}}),
    "IF": ("architecture", "architecture", {"Between": {"ARCH", "EXT"}, "Satisfies": {"REQ"}}),
    "DES": ("design", "design", {"Refines": {"ARCH", "IF"}}),
    "UT": ("unit", "verification/unit", {"Verifies": {"DES"}}),
    "IT": ("integration", "verification/integration", {"Verifies": {"DES", "IF"}}),
    "ST": ("system", "verification/system", {"Verifies": {"ARCH", "IF", "SCN"}}),
    "AT": ("acceptance", "acceptance", {"Verifies": {"REQ"}}),
}
LINK_FIELDS = {f for _, _, links in TYPES.values() for f in links}
TEST_DIRS = {"UT": "unit", "IT": "integration", "ST": "system", "AT": "acceptance"}
ACCEPTING_VERDICTS = {"accepted", "waived"}
VERDICTS = ACCEPTING_VERDICTS | {"rejected"}
VERDICT_ROW_RE = re.compile(r"^\|\s*\**((?:CON|REQ)-\d{3,})\**\s*\|\s*\**\s*([A-Za-z]+)[^|]*\|(.*)$")

CODE_EXTS = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".kts",
    ".swift", ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".rb", ".php", ".scala", ".sh", ".sql",
    ".vue", ".svelte", ".dart", ".m", ".ex", ".exs", ".lua",
}
SKIP_DIRS = {"node_modules", "__pycache__", ".venv", "venv", "dist", "build", "target", ".git"}

ID_RE = re.compile(r"\b([A-Z]+-\d{3,})\b")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
ITEM_HEADING_RE = re.compile(r"^([A-Z]+-\d{3,})\b(.*)$")
FIELD_RE = re.compile(r"^\s*[-*]\s+\**\s*([A-Za-z]+)\s*\**\s*:\s*\**\s*(.*)$")
TAG_IDS = r"((?:[A-Z]+-\d{3,}[\s,]*)+)"
IMPLEMENTS_RE = re.compile(r"@implements\s+" + TAG_IDS)
TEST_TAG_RE = re.compile(r"@test\s+" + TAG_IDS)
EXEMPT_RE = re.compile(r"@trace-exempt\b")

# EARS: [Where <feature>,] [While <state>,] [When <trigger>, | If <condition>, then] the <system> shall <response>
EARS_RE = re.compile(
    r"^(?:Where\s+(?P<where>.+?),\s+)?"
    r"(?:While\s+(?P<while>.+?),\s+)?"
    r"(?:When\s+(?P<when>.+?),\s+|If\s+(?P<if>.+?),\s+then\s+)?"
    r"(?P<system>the\s+.+?)\s+shall\s+(?P<response>\S.*)$",
    re.IGNORECASE,
)
EARS_PATTERNS = ("ubiquitous", "event-driven", "state-driven", "unwanted", "optional", "complex")
SHALL_RE = re.compile(r"\bshall\b", re.IGNORECASE)


def ears_pattern(statement: str) -> tuple[str | None, str | None]:
    """Classify an EARS statement. Returns (pattern, None) or (None, problem)."""
    text = statement.strip().strip("`*_ ").rstrip(".").strip()
    shalls = len(SHALL_RE.findall(text))
    if shalls != 1:
        return None, f"must contain exactly one 'shall' (found {shalls})"
    m = EARS_RE.match(text)
    if not m:
        if re.match(r"^If\b", text, re.IGNORECASE) and not re.search(r",\s+then\s+", text, re.IGNORECASE):
            return None, "unwanted-behavior statements need ', then the <system> shall ...'"
        return None, ("does not match EARS ([Where <feature>,] [While <state>,] "
                      "[When <trigger>, | If <condition>, then] the <system> shall <response>)")
    clauses = [k for k in ("where", "while", "when", "if") if m.group(k)]
    if len(clauses) > 1:
        return "complex", None
    return {"where": "optional", "while": "state-driven", "when": "event-driven", "if": "unwanted"}.get(
        clauses[0] if clauses else "", "ubiquitous"
    ), None


@dataclass
class Item:
    id: str
    title: str
    path: str
    line: int
    retired: bool = False
    links: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def prefix(self) -> str:
        return self.id.split("-")[0]


@dataclass
class Issue:
    stage: str
    message: str
    where: str = ""

    def render(self) -> str:
        return f"[{self.stage}] {self.message}" + (f"  ({self.where})" if self.where else "")


@dataclass
class Model:
    root: Path
    items: dict[str, Item] = field(default_factory=dict)
    duplicates: list[tuple[str, str]] = field(default_factory=list)
    implements: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))  # id -> files
    tests: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))  # id -> files
    orphan_files: list[str] = field(default_factory=list)
    exempt_files: list[str] = field(default_factory=list)
    # CON/REQ id -> [(verdict, evidence ids, location)] from verdict tables in factory/acceptance/
    verdicts: dict[str, list[tuple[str, list[str], str]]] = field(default_factory=lambda: defaultdict(list))

    def children(self) -> dict[str, list[tuple[str, str]]]:
        """Reverse edges: upstream id -> [(downstream id, field)]."""
        rev: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for item in self.items.values():
            for fld, targets in item.links.items():
                for t in targets:
                    rev[t].append((item.id, fld))
        return rev

    def live(self, prefix: str) -> list[Item]:
        return sorted(
            (i for i in self.items.values() if i.prefix == prefix and not i.retired), key=lambda i: i.id
        )


# --------------------------------------------------------------------------- parsing


def rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def parse_markdown(model: Model, path: Path, collect_verdicts: bool = False) -> None:
    current: Item | None = None
    current_level = 0
    in_fence = False
    in_comment = False
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_comment or stripped.startswith("<!--"):
            in_comment = "-->" not in stripped
            continue
        if collect_verdicts:
            row = VERDICT_ROW_RE.match(stripped)
            if row:
                evidence = [i for i in ID_RE.findall(row.group(3)) if i.split("-")[0] in TYPES]
                model.verdicts[row.group(1)].append(
                    (row.group(2).lower(), evidence, f"{rel(model.root, path)}:{lineno}")
                )
                continue

        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            item_match = ITEM_HEADING_RE.match(text)
            if item_match and 2 <= level <= 4 and item_match.group(1).split("-")[0] in TYPES:
                item_id = item_match.group(1)
                title = item_match.group(2).lstrip(":—- ").strip()
                current = Item(item_id, title, rel(model.root, path), lineno, retired="(retired)" in title.lower())
                current_level = level
                if item_id in model.items:
                    model.duplicates.append((item_id, f"{current.path}:{lineno}"))
                else:
                    model.items[item_id] = current
                continue
            if current and level <= current_level:
                current = None
            continue

        if current is None:
            continue
        fld = FIELD_RE.match(line)
        if not fld:
            continue
        name, value = fld.group(1), fld.group(2)
        if name in LINK_FIELDS:
            for target in ID_RE.findall(value):
                if target.split("-")[0] in TYPES and target not in current.links[name]:
                    current.links[name].append(target)
        else:
            current.fields.setdefault(name, value.strip())


def iter_files(base: Path):
    if not base.is_dir():
        return
    for p in sorted(base.rglob("*")):
        if p.is_file() and not any(part in SKIP_DIRS or part.startswith(".") for part in p.relative_to(base).parts):
            yield p


def tag_ids(regex: re.Pattern, text: str) -> list[str]:
    ids: list[str] = []
    for m in regex.finditer(text):
        ids.extend(ID_RE.findall(m.group(1)))
    return ids


def load(root: Path) -> Model:
    model = Model(root)
    factory = root / "factory"
    for directory in sorted({stage_dir for _, stage_dir, _ in TYPES.values()}):
        for p in iter_files(factory / directory):
            if p.suffix == ".md":
                parse_markdown(model, p, collect_verdicts=directory == "acceptance")

    for p in iter_files(root / "src"):
        if p.suffix not in CODE_EXTS:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            continue
        ids = tag_ids(IMPLEMENTS_RE, text)
        for i in ids:
            if rel(root, p) not in model.implements[i]:
                model.implements[i].append(rel(root, p))
        if not ids:
            (model.exempt_files if EXEMPT_RE.search(text) else model.orphan_files).append(rel(root, p))

    for p in iter_files(root / "tests"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        for i in tag_ids(TEST_TAG_RE, text):
            if rel(root, p) not in model.tests[i]:
                model.tests[i].append(rel(root, p))
    return model


# --------------------------------------------------------------------------- checks


def where(item: Item) -> str:
    return f"{item.path}:{item.line}"


def check(model: Model) -> list[Issue]:
    issues: list[Issue] = []
    add = issues.append
    items = model.items
    rev = model.children()

    def live_children(item_id: str, prefixes: set[str], fld: str | None = None) -> list[str]:
        return [
            c for c, f in rev.get(item_id, [])
            if c.split("-")[0] in prefixes and not items[c].retired and (fld is None or f == fld)
        ]

    # --- structural checks, attributed to the stage of the defining item
    if not model.live("CON"):
        add(Issue("requirements", "No CON items in factory/concept/ (number concept goals as '### CON-001: ...')"))
    for dup_id, loc in model.duplicates:
        add(Issue(TYPES[dup_id.split("-")[0]][0], f"Duplicate definition of {dup_id}", loc))
    for item in items.values():
        stage, directory, allowed = TYPES[item.prefix]
        if not item.path.startswith(f"factory/{directory}/"):
            add(Issue(stage, f"{item.id} must be defined under factory/{directory}/", where(item)))
        for fld, targets in item.links.items():
            if fld not in allowed:
                add(Issue(stage, f"{item.id} uses link field '{fld}', not allowed for {item.prefix}", where(item)))
                continue
            for t in targets:
                if t not in items:
                    add(Issue(stage, f"{item.id} {fld} {t}, which is not defined", where(item)))
                elif t.split("-")[0] not in allowed[fld]:
                    add(Issue(stage, f"{item.id} {fld} {t}: {fld} may only target {sorted(allowed[fld])}", where(item)))
        linked = [t for ts in item.links.values() for t in ts if t in items]
        if not item.retired and linked and all(items[t].retired for t in linked):
            add(Issue(stage, f"{item.id} traces only to retired items {linked}", where(item)))

    def require_upstream(prefix: str, fld: str, stage: str, need: set[str] | None = None) -> None:
        for item in model.live(prefix):
            targets = [t for t in item.links.get(fld, []) if t in items and not items[t].retired]
            if need:
                targets = [t for t in targets if t.split("-")[0] in need]
            if not targets:
                extra = f" (at least one {sorted(need)})" if need else ""
                add(Issue(stage, f"{item.id} has no '{fld}' link{extra}", where(item)))

    def require_downstream(prefix: str, child_prefixes: set[str], stage: str, label: str) -> None:
        for item in model.live(prefix):
            if not live_children(item.id, child_prefixes):
                add(Issue(stage, f"{item.id} is not {label}", where(item)))

    def reaches_req(item_id: str) -> bool:
        """True if a live REQ derives from item_id, directly or through use cases / user stories."""
        stack, seen = [item_id], set()
        while stack:
            for child in live_children(stack.pop(), {"UC", "US", "REQ"}, "Source"):
                if child.startswith("REQ-"):
                    return True
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
        return False

    # --- requirements
    for item in model.live("CON"):
        if not reaches_req(item.id):
            add(Issue("requirements", f"{item.id} is not covered by any REQ (directly or via UC/US)", where(item)))
    for item in model.live("UC"):
        if not reaches_req(item.id):
            add(Issue("requirements", f"{item.id} is not refined into any REQ (directly or via US)", where(item)))
    require_upstream("UC", "Source", "requirements")
    require_upstream("US", "Source", "requirements")
    require_upstream("REQ", "Source", "requirements")
    require_upstream("SCN", "Covers", "requirements", need={"REQ"})
    require_downstream("UC", {"SCN"}, "requirements", "covered by any SCN (Covers)")
    for item in model.live("REQ"):
        statement = item.fields.get("Statement", "")
        if not statement:
            add(Issue("requirements", f"{item.id} has no 'Statement' (EARS)", where(item)))
            continue
        detected, problem = ears_pattern(statement)
        if problem:
            add(Issue("requirements", f"{item.id} Statement is not valid EARS: {problem}", where(item)))
            continue
        declared = item.fields.get("EARS", "").strip("`*_ ").lower()
        if declared not in EARS_PATTERNS:
            add(Issue("requirements", f"{item.id} needs an 'EARS' field, one of {list(EARS_PATTERNS)} "
                                      f"(statement reads as {detected})", where(item)))
        elif declared != detected:
            add(Issue("requirements", f"{item.id} declares EARS '{declared}' but the statement reads as "
                                      f"'{detected}'", where(item)))
    require_downstream("US", {"REQ"}, "requirements", "refined into any REQ (Source)")

    # --- architecture
    require_downstream("REQ", {"ARCH", "IF"}, "architecture", "allocated to any ARCH/IF (Satisfies)")
    require_upstream("ARCH", "Satisfies", "architecture")
    require_upstream("IF", "Between", "architecture", need={"ARCH"})

    # --- design
    require_downstream("ARCH", {"DES"}, "design", "refined by any DES")
    require_upstream("DES", "Refines", "design", need={"ARCH"})

    # --- implementation
    for item in model.live("DES"):
        if not model.implements.get(item.id):
            add(Issue("implementation", f"{item.id} has no implementing code (@implements {item.id})", where(item)))
    for tag_id, files in sorted(model.implements.items()):
        if tag_id not in items:
            add(Issue("implementation", f"@implements {tag_id} references an undefined item", ", ".join(files)))
        elif items[tag_id].prefix != "DES":
            add(Issue("implementation", f"@implements {tag_id}: code must implement DES items", ", ".join(files)))
        elif items[tag_id].retired:
            add(Issue("implementation", f"@implements {tag_id}: item is retired", ", ".join(files)))
    for f in model.orphan_files:
        add(Issue("implementation", "Source file has no @implements tag (or @trace-exempt <reason>)", f))

    # --- test cases at every right-side level: upstream link + automation in the right directory
    for prefix, level_dir in TEST_DIRS.items():
        stage = TYPES[prefix][0]
        require_upstream(prefix, "Verifies", stage)
        for item in model.live(prefix):
            if not model.tests.get(item.id):
                add(Issue(stage, f"{item.id} has no automated test (@test {item.id})", where(item)))
    for tag_id, files in sorted(model.tests.items()):
        prefix = tag_id.split("-")[0]
        if prefix not in TEST_DIRS:
            add(Issue("unit", f"@test {tag_id}: tag must reference a UT/IT/ST/AT case", ", ".join(files)))
            continue
        stage = TYPES[prefix][0]
        if tag_id not in items:
            add(Issue(stage, f"@test {tag_id} references an undefined test case", ", ".join(files)))
        for f in files:
            if not f.startswith(f"tests/{TEST_DIRS[prefix]}/"):
                add(Issue(stage, f"@test {tag_id} must live under tests/{TEST_DIRS[prefix]}/", f))

    def between(interface: Item) -> list[str]:
        return [t for t in interface.links.get("Between", []) if t in items and not items[t].retired]

    internal_ifs = [i for i in model.live("IF") if between(i) and all(t.startswith("ARCH-") for t in between(i))]
    external_ifs = [i for i in model.live("IF") if any(t.startswith("EXT-") for t in between(i))]

    # --- unit testing <-> implementation: every implemented design unit is unit-tested
    require_downstream("DES", {"UT"}, "unit", "verified by any UT")

    # --- integration testing <-> design: units and components work together as designed
    for interface in internal_ifs:
        if not live_children(interface.id, {"IT"}):
            add(Issue("integration", f"{interface.id} (internal interface) is not verified by any IT", where(interface)))
    for comp in model.live("ARCH"):
        units = live_children(comp.id, {"DES"})
        if len(units) < 2:
            continue
        comp_ifs = [i.id for i in internal_ifs if comp.id in between(i)]
        if not any(live_children(x, {"IT"}) for x in units + comp_ifs):
            add(Issue("integration", f"{comp.id} has {len(units)} design units but no IT verifies their "
                                     f"collaboration (Verifies one of its DES or interfaces)", where(comp)))

    # --- system testing <-> architecture: the complete system, as architected, end to end
    require_downstream("ARCH", {"ST"}, "system", "exercised by any ST")
    for interface in external_ifs:
        if not live_children(interface.id, {"ST"}):
            add(Issue("system", f"{interface.id} (external interface) is not verified by any ST", where(interface)))
    require_downstream("SCN", {"ST"}, "system", "verified end to end by any ST")

    # --- acceptance <-> requirements: every requirement accepted, with evidence
    require_downstream("REQ", {"AT"}, "acceptance", "verified by any AT")
    for item_id, rows in sorted(model.verdicts.items()):
        for verdict, evidence, loc in rows:
            if item_id not in items:
                add(Issue("acceptance", f"Verdict for {item_id}, which is not defined", loc))
            if verdict not in VERDICTS:
                add(Issue("acceptance", f"Verdict for {item_id} must be accepted|rejected|waived, not '{verdict}'", loc))
            for e in evidence:
                if e not in items:
                    add(Issue("acceptance", f"Verdict for {item_id} cites {e}, which is not defined", loc))
    for prefix in ("CON", "REQ"):
        for item in model.live(prefix):
            rows = model.verdicts.get(item.id, [])
            if not rows:
                add(Issue("acceptance", f"{item.id} has no verdict in the acceptance report", where(item)))
            elif any(v not in ACCEPTING_VERDICTS for v, _, _ in rows):
                add(Issue("acceptance", f"{item.id} is not accepted ({rows[0][2]})", where(item)))
            elif prefix == "REQ" and any(v == "accepted" and not e for v, e, _ in rows):
                add(Issue("acceptance", f"{item.id} verdict cites no evidence (AT/ST/IT/UT IDs)", rows[0][2]))
    return issues


# --------------------------------------------------------------------------- impact & matrix


def impact(model: Model, ids: list[str]) -> dict[str, list[str]]:
    rev = model.children()
    seen: set[str] = set()
    queue = list(ids)
    while queue:
        cur = queue.pop()
        for child, _ in rev.get(cur, []):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    result: dict[str, list[str]] = defaultdict(list)
    for i in sorted(seen | set(ids)):
        if i in model.items and i not in ids:
            result[i.split("-")[0]].append(i)
    affected = seen | set(ids)
    result["code"] = sorted({f for i in affected for f in model.implements.get(i, [])})
    result["tests"] = sorted({f for i in affected for f in model.tests.get(i, [])})
    return {k: v for k, v in result.items() if v}


def matrix(model: Model, issues: list[Issue], gate: str) -> str:
    rev = model.children()
    items = model.items

    def kids(i: str, prefixes: set[str]) -> str:
        found = sorted({c for c, _ in rev.get(i, []) if c.split("-")[0] in prefixes})
        return ", ".join(found) or "—"

    def ups(item: Item, fld: str) -> str:
        return ", ".join(item.links.get(fld, [])) or "—"

    def verdict(i: str) -> str:
        return ", ".join(v for v, _, _ in model.verdicts.get(i, [])) or "—"

    def name(item: Item) -> str:
        return f"{item.id}{' (retired)' if item.retired else ''}"

    out = ["# Traceability Matrix", "", "_Generated by `scripts/trace_check.py`. Do not edit._", ""]
    counts = {p: len(model.live(p)) for p in TYPES}
    out += ["## Summary", "", "| " + " | ".join(counts) + " |", "|" + "---|" * len(counts),
            "| " + " | ".join(str(v) for v in counts.values()) + " |", ""]
    errors = [i for i in issues if GATES.index(i.stage) <= GATES.index(gate)]
    out += [f"Gate `{gate}`: **{'PASS' if not errors else f'FAIL ({len(errors)} errors)'}**", ""]

    sections = [
        ("Concept goals", "CON",
         ["Concept goal", "Use cases", "User stories", "Requirements (direct)", "Acceptance verdict"],
         lambda it: [kids(it.id, {"UC"}), kids(it.id, {"US"}), kids(it.id, {"REQ"}), verdict(it.id)]),
        ("Use cases", "UC", ["Use case", "Source", "User stories", "Requirements", "Scenarios"],
         lambda it: [ups(it, "Source"), kids(it.id, {"US"}), kids(it.id, {"REQ"}), kids(it.id, {"SCN"})]),
        ("User stories", "US", ["User story", "Source", "Requirements"],
         lambda it: [ups(it, "Source"), kids(it.id, {"REQ"})]),
        ("Requirements ↔ Acceptance", "REQ",
         ["Requirement", "EARS", "Source", "Scenarios", "Allocated to", "Acceptance tests", "Verdict"],
         lambda it: [it.fields.get("EARS", "—") or "—", ups(it, "Source"), kids(it.id, {"SCN"}),
                     kids(it.id, {"ARCH", "IF"}), kids(it.id, {"AT"}), verdict(it.id)]),
        ("Scenarios", "SCN", ["Scenario", "Covers", "System tests"],
         lambda it: [ups(it, "Covers"), kids(it.id, {"ST"})]),
        ("Architecture ↔ System testing: components", "ARCH",
         ["Component", "Satisfies", "Interfaces", "Design units", "System tests"],
         lambda it: [ups(it, "Satisfies"), kids(it.id, {"IF"}), kids(it.id, {"DES"}), kids(it.id, {"ST"})]),
        ("Architecture: interfaces", "IF",
         ["Interface", "Between", "Satisfies", "Design units", "Integration tests", "System tests"],
         lambda it: [ups(it, "Between"), ups(it, "Satisfies"), kids(it.id, {"DES"}), kids(it.id, {"IT"}),
                     kids(it.id, {"ST"})]),
        ("Design ↔ Integration testing, Implementation ↔ Unit testing", "DES",
         ["Design unit", "Refines", "Integration tests", "Code", "Unit tests"],
         lambda it: [ups(it, "Refines"), kids(it.id, {"IT"}), ", ".join(model.implements.get(it.id, [])) or "—",
                     kids(it.id, {"UT"})]),
    ]
    for title, prefix, headers, row in sections:
        rows = sorted((i for i in items.values() if i.prefix == prefix), key=lambda i: i.id)
        if not rows:
            continue
        out += [f"## {title}", "", "| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
        out += ["| " + " | ".join([name(it)] + row(it)) + " |" for it in rows]
        out.append("")

    tests = sorted((i for i in items.values() if i.prefix in TEST_DIRS), key=lambda i: i.id)
    if tests:
        out += ["## Test cases", "", "| Test case | Verifies | Automated in |", "|---|---|---|"]
        out += [f"| {name(t)} | {ups(t, 'Verifies')} | {', '.join(model.tests.get(t.id, [])) or '—'} |" for t in tests]
        out.append("")
    if issues:
        out += ["## Issues", ""] + [f"- {i.render()}" for i in issues] + [""]
    return "\n".join(out)


# --------------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V-model traceability checker")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--gate", choices=GATES, default="acceptance")
    parser.add_argument("--impact", nargs="+", metavar="ID")
    parser.add_argument("--matrix", nargs="?", const="factory/trace/matrix.md", metavar="PATH",
                        help="write the matrix (default path factory/trace/matrix.md; implied by --gate acceptance)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    model = load(root)

    if args.impact:
        unknown = [i for i in args.impact if i not in model.items]
        result = impact(model, args.impact)
        if args.json:
            print(json.dumps({"ids": args.impact, "unknown": unknown, "impact": result}, indent=2))
        else:
            if unknown:
                print(f"Unknown IDs: {', '.join(unknown)}")
            print(f"Downstream impact of {', '.join(args.impact)}:")
            for key, values in result.items():
                print(f"  {key}: {', '.join(values)}")
            if not result:
                print("  (nothing downstream)")
        return 1 if unknown else 0

    issues = check(model)
    gate_idx = GATES.index(args.gate)
    errors = [i for i in issues if GATES.index(i.stage) <= gate_idx]
    warnings = [i for i in issues if GATES.index(i.stage) > gate_idx]

    matrix_path = args.matrix or ("factory/trace/matrix.md" if args.gate == "acceptance" else None)
    if matrix_path:
        target = (root / matrix_path) if not Path(matrix_path).is_absolute() else Path(matrix_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(matrix(model, issues, args.gate), encoding="utf-8")

    counts = {p: len(model.live(p)) for p in TYPES}
    if args.json:
        print(json.dumps({
            "gate": args.gate, "pass": not errors, "counts": counts,
            "errors": [i.__dict__ for i in errors], "warnings": [i.__dict__ for i in warnings],
        }, indent=2))
    else:
        print("Items: " + ", ".join(f"{k}={v}" for k, v in counts.items() if v) if any(counts.values()) else "Items: none")
        for i in errors:
            print(f"ERROR   {i.render()}")
        for i in warnings:
            print(f"warning {i.render()}")
        print(f"Gate '{args.gate}': {'PASS' if not errors else 'FAIL'} "
              f"({len(errors)} errors, {len(warnings)} warnings beyond this gate)")
        if matrix_path:
            print(f"Matrix written to {matrix_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
