"""Root test configuration: opt-in gating for the live ACL suite.

``tests/acl`` drives real role swaps and ACL changes against a tenant, so it never runs
by accident. Pass ``--run-acl`` to enable it; without the flag every test collected under
``tests/acl`` is skipped. See ``tests/acl/TESTING.md``.
"""

from pathlib import Path

import pytest

ACL_DIR = Path(__file__).parent / "acl"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-acl",
        action="store_true",
        default=False,
        help="Run the live ACL suite in tests/acl (mutates roles and ACLs on the tenant).",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_acl = config.getoption("--run-acl")
    skip_acl = pytest.mark.skip(reason="live ACL suite: pass --run-acl to enable")
    for item in items:
        if ACL_DIR not in Path(item.fspath).parents:
            continue
        item.add_marker(pytest.mark.acl)
        item.add_marker(pytest.mark.acl_likely)
        if not run_acl:
            item.add_marker(skip_acl)


_ACL_REPORTS: list[pytest.TestReport] = []


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.when == "call" and report.user_properties:
        _ACL_REPORTS.append(report)


def pytest_sessionfinish(session: pytest.Session) -> None:
    if hasattr(session.config, "workerinput") or not session.config.getoption("--run-acl"):
        return
    from tests.acl import report

    rows = report.rows_from_reports(_ACL_REPORTS)
    if rows:
        report.write(rows, Path(session.config.rootpath) / "acl-report")
