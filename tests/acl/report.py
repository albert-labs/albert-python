"""Collect one row per ACL check and write ``acl-report.md`` / ``acl-report.csv``.

Rows are attached to the pytest item as ``user_properties`` so they survive xdist; the
controller writes the report at session finish, grouped by policy/level and verdict.
"""

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import pytest

from tests.acl.oracle import FAILING, Verdict

REPORT_KEY = "acl_row"


@dataclass(frozen=True)
class Row:
    scenario: str
    subject: str
    action: str
    expect: str
    status: int | None
    verdict: str
    detail: str = ""


def record(request: pytest.FixtureRequest, row: Row) -> None:
    request.node.user_properties.append((REPORT_KEY, json.dumps(asdict(row))))


def rows_from_reports(reports) -> list[Row]:
    rows = []
    for rep in reports:
        for key, value in getattr(rep, "user_properties", ()):
            if key == REPORT_KEY:
                rows.append(Row(**json.loads(value)))
    return rows


def write(rows: list[Row], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "acl-report.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(Row.__dataclass_fields__))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    (out_dir / "acl-report.md").write_text(render_markdown(rows))


def render_markdown(rows: list[Row]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.verdict] += 1
    lines = ["# ACL report", "", "| verdict | count |", "|---|---|"]
    lines += [f"| {v} | {n} |" for v, n in sorted(counts.items())]
    failing = {v.value for v in FAILING}
    by_subject: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        if row.verdict in failing:
            by_subject[row.subject].append(row)
    lines += ["", "## Findings by policy / level", ""]
    if not by_subject:
        lines.append("No findings.")
    for subject in sorted(by_subject):
        lines += [
            f"### {subject}",
            "",
            "| scenario | action | expected | status | verdict | detail |",
        ]
        lines.append("|---|---|---|---|---|---|")
        for r in by_subject[subject]:
            lines.append(
                f"| {r.scenario} | {r.action} | {r.expect} | {r.status} | {r.verdict} | {r.detail} |"
            )
        lines.append("")
    undecided = [r for r in rows if r.verdict == Verdict.UNDECIDED.value]
    lines += ["## Undecided (ask product)", ""]
    lines += [f"- {r.subject} / {r.action}: {r.detail}" for r in undecided] or ["None."]
    inconclusive = [r for r in rows if r.verdict == Verdict.INCONCLUSIVE.value]
    lines += ["", "## Inconclusive (probe or payload problem)", ""]
    lines += [f"- {r.subject} / {r.action}: {r.status} {r.detail}" for r in inconclusive] or [
        "None."
    ]
    return "\n".join(lines) + "\n"
