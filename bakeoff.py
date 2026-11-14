# ai-generated: 90% - Claude Code wrote the rules from CI-SPEC.md section 3 on the course skeleton; I check the output against expected.json
"""bakeoff.py - scanner SARIF + a labels file -> a per-tool confusion matrix (CI-SPEC.md P-23).

Implements P-14 to P-22. Standard library only - it runs as `python3 -S -E bakeoff.py`.

    python3 bakeoff.py --labels labels.json a.sarif b.sarif > bakeoff.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import unquote

# P-15: tool names that map to fixed tool ids.
KNOWN_TOOLS = {"trivy", "grype", "osv-scanner", "gitleaks"}
SEMGREP_NAMES = {"semgrep", "semgrep oss", "semgrep ce", "semgrep community edition", "semgrep pro"}

# P-19: the course's classes and their CWE lists (section 3.2).
CLASS_CWES: dict[str, set[int]] = {
    "secret": {259, 260, 321, 798},
    "injection": {74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336},
    "deserialization": {502},
    "weak-crypto": {261, 326, 327, 328, 330, 331, 338, 759, 760, 916},
    "insecure-transport": {295, 297, 319, 322, 757},
    "path-traversal": {22, 23, 35, 36, 73},
    "ssrf": {918},
    "vulnerable-dependency": {937, 1035, 1104, 1395},
    "misconfiguration": {16, 215, 250, 489, 668, 732, 1188},
    "access-control": {284, 285, 639, 862, 863},
}
CLASSES = set(CLASS_CWES)

CWE_TAG = re.compile(r"(?<![A-Za-z0-9])[Cc][Ww][Ee]-([0-9]+)")
PEP503_SEP = re.compile(r"[-_.]+")
TOKEN = re.compile(r"[A-Za-z0-9._-]+")


def is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def as_list(value) -> list:
    return value if isinstance(value, list) else []


def string_entries(value) -> list[str]:
    return [entry for entry in as_list(value) if isinstance(entry, str)]


def tool_id(run: dict) -> str:
    """P-15: the tool id of a run."""
    name = as_dict(as_dict(run.get("tool")).get("driver")).get("name")
    if not isinstance(name, str):
        return "unknown"
    lowered = name.strip().lower()
    if lowered in KNOWN_TOOLS:
        return lowered
    if lowered in SEMGREP_NAMES:
        return "semgrep"
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "unknown"


def normalize_path(uri: str) -> str:
    """P-17: percent-decoding, then file:// removal, then one leading ./ removal."""
    path = unquote(uri)
    if path[:7].lower() == "file://":
        path = path[7:]
    if path.startswith("./"):
        path = path[2:]
    return path


def set_relative_file(path: str, root: str) -> str | None:
    """P-17: the file from the last component equal to the set root, or None when outside the set."""
    parts = path.split("/")
    indexes = [i for i, part in enumerate(parts) if part == root]
    if not indexes:
        return None
    return "/".join(parts[indexes[-1]:])


def result_record(result, run: dict, tool: str, rules_by_id: dict, root: str) -> dict | None:
    """P-16 to P-19: one result of a run, or None when it is dropped or outside the set."""
    if not isinstance(result, dict):
        return None
    kind = result.get("kind")
    if kind is not None and kind != "fail":
        return None
    suppressions = result.get("suppressions")
    if suppressions is not None and suppressions:
        return None
    locations = as_list(result.get("locations"))
    if not locations or not isinstance(locations[0], dict):
        return None
    physical = as_dict(locations[0].get("physicalLocation"))
    uri = as_dict(physical.get("artifactLocation")).get("uri")
    if not isinstance(uri, str) or not uri:
        return None
    file = set_relative_file(normalize_path(uri), root)
    if file is None:
        return None

    # P-18: lines.
    start = end = None
    region = as_dict(physical.get("region"))
    start_line = region.get("startLine")
    if is_int(start_line) and start_line >= 1:
        start = start_line
        end_line = region.get("endLine")
        end = end_line if is_int(end_line) and end_line >= start else start

    # P-19: the rule and the classes.
    rule_id = result.get("ruleId")
    if not isinstance(rule_id, str):
        rule_id = None
    rule = rules_by_id.get(rule_id) if rule_id is not None else None
    rule_tags = string_entries(as_dict(as_dict(rule).get("properties")).get("tags"))
    result_tags = string_entries(as_dict(result.get("properties")).get("tags"))
    classes = classes_of(result, tool, rule_tags, result_tags)

    message = as_dict(result.get("message")).get("text")
    text = message if isinstance(message, str) else None
    return {
        "tool": tool,
        "rule_id": rule_id,
        "file": file,
        "start": start,
        "end": end,
        "classes": classes,
        "text": text,
    }


def classes_of(result: dict, tool: str, rule_tags: list[str], result_tags: list[str]) -> set[str]:
    """P-19 (a), (b), (c); an empty set is class `other`."""
    own = as_dict(result.get("properties")).get("class")
    if isinstance(own, str) and own in CLASSES:
        return {own}
    if tool == "gitleaks":
        return {"secret"}
    if tool in ("grype", "osv-scanner"):
        return {"vulnerable-dependency"}
    if tool == "trivy":
        mapped = {
            "vulnerability": "vulnerable-dependency",
            "secret": "secret",
            "misconfiguration": "misconfiguration",
        }
        found = {mapped[tag.lower()] for tag in rule_tags if tag.lower() in mapped}
        if found:
            return found
    numbers: set[int] = set()
    for tag in result_tags + rule_tags:
        numbers.update(int(match) for match in CWE_TAG.findall(tag))
    return {cls for cls, cwes in CLASS_CWES.items() if cwes & numbers}


def package_tokens(text: str) -> set[str]:
    """P-20: the PEP 503-normalised tokens of a message."""
    tokens = set()
    for raw in TOKEN.findall(text):
        token = raw.strip("._-")
        if token:
            tokens.add(PEP503_SEP.sub("-", token.lower()))
    return tokens


def matches(record: dict, defect: dict) -> bool:
    """P-20: whether a result matches a defect."""
    if record["file"] != defect["file"]:
        return False
    cls = defect["class"]
    if cls not in record["classes"]:
        return False
    if cls == "vulnerable-dependency":
        if record["text"] is None:
            return False
        package = PEP503_SEP.sub("-", str(defect.get("package", "")).lower())
        return package in package_tokens(record["text"])
    if record["start"] is None:
        return False
    return record["start"] <= defect["end_line"] and defect["start_line"] <= record["end"]


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def confusion_matrix(labels: dict, sarif_documents: list[dict]) -> dict:
    """The matrix of P-21 and P-22 for the labels (P-14) and the parsed SARIF documents."""
    root = labels["set"]
    defects = as_list(labels.get("defects"))

    records_by_tool: dict[str, list[dict]] = {}
    for document in sarif_documents:
        for run in as_list(as_dict(document).get("runs")):
            if not isinstance(run, dict):
                continue
            tool = tool_id(run)
            records = records_by_tool.setdefault(tool, [])
            driver = as_dict(as_dict(run.get("tool")).get("driver"))
            rules_by_id: dict = {}
            for rule in as_list(driver.get("rules")):
                if isinstance(rule, dict) and isinstance(rule.get("id"), str):
                    rules_by_id.setdefault(rule["id"], rule)
            for result in as_list(run.get("results")):
                record = result_record(result, run, tool, rules_by_id, root)
                if record is not None:
                    records.append(record)

    tools: dict[str, dict] = {}
    for tool, records in records_by_tool.items():
        matched: set[int] = set()
        false_positives: set[tuple] = set()
        for record in records:
            hits = [i for i, defect in enumerate(defects) if matches(record, defect)]
            if hits:
                matched.update(hits)
            else:
                false_positives.add((record["rule_id"], record["file"], record["start"], record["end"]))
        tp = len(matched)
        fp = len(false_positives)
        fn = len(defects) - tp
        tools[tool] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn),
            "f1": ratio(2 * tp, 2 * tp + fp + fn),
        }
    return {"set": root, "defects": len(defects), "tools": tools}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="per-tool confusion matrix of SARIF against labels (CI-SPEC.md P-23)")
    parser.add_argument("--labels", required=True, help="the labels file (P-14)")
    parser.add_argument("sarif", nargs="+", help="SARIF 2.1.0 files")
    args = parser.parse_args(argv)
    with open(args.labels, encoding="utf-8-sig") as fh:
        labels = json.load(fh)
    documents = []
    for path in args.sarif:
        with open(path, encoding="utf-8-sig") as fh:  # -sig: a byte-order mark is not an error
            documents.append(json.load(fh))
    json.dump(confusion_matrix(labels, documents), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
