"""Manual smoke test for SEA-158 search filters against the dev environment.

Usage:
    set -a && source ~/.env.dev && set +a
    uv run python scripts/test_search_api_drift.py
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from albert import Albert
from albert.resources.inventory import InventoryCategory
from albert.resources.users import User

load_dotenv(Path.home() / ".env.dev")

REQUIRED = ("ALBERT_CLIENT_ID_SDK", "ALBERT_CLIENT_SECRET_SDK", "ALBERT_BASE_URL")
missing = [name for name in REQUIRED if not os.getenv(name)]
if missing:
    sys.exit(f"Missing required env vars from ~/.env.dev: {', '.join(missing)}")

client = Albert()
ALL_RESULTS: dict[str, dict[str, bool | str]] = {}


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def show_count(label: str, items: list) -> None:
    print(f"{label}: {len(items)} result(s)")
    for item in items[:3]:
        print(f"  - {item}")


def verify_user_identity(creator_name: str | None, creator_id: str | None) -> None:
    if not creator_id:
        return
    try:
        user = client.users.get_by_id(id=creator_id)
        match = user.name == creator_name
        print(
            f"  identity check: {creator_id!r} -> users.get_by_id name={user.name!r} "
            f"(matches baseline name {creator_name!r}: {match})"
        )
    except Exception as exc:
        print(f"  identity check failed for {creator_id!r}: {exc}")


def compare_result_ids(
    label: str,
    *,
    name_hits: list[Any] | None,
    id_hits: list[Any] | None,
    baseline_id: str | None,
    id_attr: str = "id",
) -> str:
    if name_hits is None or id_hits is None:
        return "SKIP (filter not run)"

    name_ids = {getattr(h, id_attr) for h in name_hits}
    user_ids = {getattr(h, id_attr) for h in id_hits}

    if not name_ids and not user_ids:
        return "PASS (both empty)"
    if not name_ids or not user_ids:
        return f"MISMATCH (name={len(name_ids)} ids, userId={len(user_ids)} ids)"
    if name_ids == user_ids:
        return f"PASS (same {len(name_ids)} item(s))"
    overlap = name_ids & user_ids
    if baseline_id and baseline_id in name_ids and baseline_id in user_ids:
        return f"PARTIAL (baseline in both; overlap {len(overlap)}/{len(name_ids | user_ids)})"
    return f"MISMATCH (overlap {len(overlap)}/{len(name_ids | user_ids)})"


def run_filter_with_hits(label: str, fn: Callable[[], Iterator[Any]]) -> tuple[bool, list[Any]]:
    try:
        hits = list(fn())
        suffix = "" if hits else " (0 results, no API error)"
        print(f"  PASS {label}{suffix}: {len(hits)} result(s)")
        return True, hits
    except Exception as exc:
        print(f"  FAIL {label}: {exc}")
        return False, []


def extract_audit_identities(
    item: Any,
) -> tuple[str | None, str | None, str | None, str | None]:
    creator_name = getattr(item, "created_by_name", None)
    creator_id = getattr(item, "created_by", None)

    created = getattr(item, "created", None)
    if created is not None:
        creator_id = creator_id or getattr(created, "by", None)
        creator_name = creator_name or getattr(created, "by_name", None)

    owner = getattr(item, "owner", None)
    if owner:
        first_owner = owner[0]
        creator_id = creator_id or getattr(first_owner, "id", None)
        creator_name = creator_name or getattr(first_owner, "name", None)

    updater_name = None
    updater_id = None
    updated = getattr(item, "updated", None)
    if updated is not None:
        updater_id = getattr(updated, "by", None)
        updater_name = getattr(updated, "by_name", None)

    return creator_name, creator_id, updater_name, updater_id


def safe_baseline(label: str, fn: Callable[[], Any | None]) -> Any | None:
    try:
        return fn()
    except Exception as exc:
        print(f"  SKIP {label} baseline: {exc}")
        return None


def test_str_user_filters(
    collection: str,
    *,
    baseline_fn: Callable[[], Any | None],
    search_fn: Callable[..., Iterator[Any]],
    hydrate: Callable[[Any], Any] | None = None,
    supports_updated: bool = True,
    created_by_name_only: bool = False,
    created_by_user_id_only: bool = False,
) -> None:
    print(f"\n--- {collection} created_by / updated_by ---")
    baseline = safe_baseline(collection, baseline_fn)
    if baseline is None:
        print("  SKIP: no baseline hit")
        ALL_RESULTS[collection] = {"baseline": "SKIP (no hit)"}
        return

    item = hydrate(baseline) if hydrate else baseline
    creator_name, creator_id, updater_name, updater_id = extract_audit_identities(item)
    print(
        f"  baseline creator: name={creator_name!r} id={creator_id!r} | "
        f"updater: name={updater_name!r} id={updater_id!r}"
    )
    verify_user_identity(creator_name, creator_id)
    if updater_id and updater_id != creator_id:
        verify_user_identity(updater_name, updater_id)

    results: dict[str, bool | str] = {}
    baseline_id = getattr(item, "id", None)

    created_by_name_hits: list[Any] | None = None
    created_by_id_hits: list[Any] | None = None

    if not created_by_user_id_only:
        if creator_name:
            ok, created_by_name_hits = run_filter_with_hits(
                f"created_by[name]={creator_name!r}",
                lambda: search_fn(created_by=[creator_name], max_items=10),
            )
            results["created_by[name]"] = ok
        else:
            print("  SKIP created_by[name]: no creator name on baseline")
            results["created_by[name]"] = "SKIP (no creator name)"

    if not created_by_name_only:
        if creator_id:
            ok, created_by_id_hits = run_filter_with_hits(
                f"created_by[userId]={creator_id!r}",
                lambda: search_fn(created_by=[creator_id], max_items=10),
            )
            results["created_by[userId]"] = ok
        else:
            print("  SKIP created_by[userId]: no creator id on baseline")
            results["created_by[userId]"] = "SKIP (no creator id)"

    if created_by_name_hits is not None and created_by_id_hits is not None:
        comparison = compare_result_ids(
            "created_by",
            name_hits=created_by_name_hits,
            id_hits=created_by_id_hits,
            baseline_id=baseline_id,
        )
        print(f"  created_by result parity: {comparison}")
        results["created_by[same items]"] = comparison

    updated_by_name_hits: list[Any] | None = None
    updated_by_id_hits: list[Any] | None = None

    if supports_updated:
        if updater_name:
            ok, updated_by_name_hits = run_filter_with_hits(
                f"updated_by[name]={updater_name!r}",
                lambda: search_fn(updated_by=[updater_name], max_items=10),
            )
            results["updated_by[name]"] = ok
        else:
            print("  SKIP updated_by[name]: no updater name on baseline")
            results["updated_by[name]"] = "SKIP (no updater name)"

        if updater_id:
            ok, updated_by_id_hits = run_filter_with_hits(
                f"updated_by[userId]={updater_id!r}",
                lambda: search_fn(updated_by=[updater_id], max_items=10),
            )
            results["updated_by[userId]"] = ok
        else:
            print("  SKIP updated_by[userId]: no updater id on baseline")
            results["updated_by[userId]"] = "SKIP (no updater id)"

        if updated_by_name_hits is not None and updated_by_id_hits is not None:
            comparison = compare_result_ids(
                "updated_by",
                name_hits=updated_by_name_hits,
                id_hits=updated_by_id_hits,
                baseline_id=baseline_id,
            )
            print(f"  updated_by result parity: {comparison}")
            results["updated_by[same items]"] = comparison

    ALL_RESULTS[collection] = results


def test_inventory_user_filters() -> None:
    print("\n--- inventory created_by / updated_by ---")

    baseline = safe_baseline(
        "inventory",
        lambda: next(iter(client.inventory.search(max_items=1)), None),
    )
    if baseline is None:
        ALL_RESULTS["inventory"] = {"baseline": "SKIP (no hit or error)"}
        return

    item = baseline.hydrate()
    creator_name, creator_id, updater_name, updater_id = extract_audit_identities(item)
    print(
        f"  baseline creator: name={creator_name!r} id={creator_id!r} | "
        f"updater: name={updater_name!r} id={updater_id!r}"
    )
    verify_user_identity(creator_name, creator_id)
    if updater_id and updater_id != creator_id:
        verify_user_identity(updater_name, updater_id)

    results: dict[str, bool | str] = {}
    baseline_id = getattr(item, "id", None)

    created_by_name_hits: list[Any] | None = None
    created_by_id_hits: list[Any] | None = None

    if creator_name:
        ok, created_by_name_hits = run_filter_with_hits(
            f"created_by[name]={creator_name!r}",
            lambda: client.inventory.search(created_by=User(name=creator_name), max_items=10),
        )
        results["created_by[name]"] = ok
    else:
        print("  SKIP created_by[name]: no creator name on baseline")
        results["created_by[name]"] = "SKIP (no creator name)"

    if creator_id:
        ok, created_by_id_hits = run_filter_with_hits(
            f"created_by[userId]={creator_id!r}",
            lambda: client.inventory.search(created_by=User(name=creator_id), max_items=10),
        )
        results["created_by[userId]"] = ok
    else:
        print("  SKIP created_by[userId]: no creator id on baseline")
        results["created_by[userId]"] = "SKIP (no creator id)"

    if created_by_name_hits is not None and created_by_id_hits is not None:
        comparison = compare_result_ids(
            "created_by",
            name_hits=created_by_name_hits,
            id_hits=created_by_id_hits,
            baseline_id=baseline_id,
        )
        print(f"  created_by result parity: {comparison}")
        results["created_by[same items]"] = comparison

    updated_by_name_hits: list[Any] | None = None
    updated_by_id_hits: list[Any] | None = None

    if updater_name:
        ok, updated_by_name_hits = run_filter_with_hits(
            f"updated_by[name]={updater_name!r}",
            lambda: client.inventory.search(updated_by=User(name=updater_name), max_items=10),
        )
        results["updated_by[name]"] = ok
    else:
        print("  SKIP updated_by[name]: no updater name on baseline")
        results["updated_by[name]"] = "SKIP (no updater name)"

    if updater_id:
        ok, updated_by_id_hits = run_filter_with_hits(
            f"updated_by[userId]={updater_id!r}",
            lambda: client.inventory.search(updated_by=User(name=updater_id), max_items=10),
        )
        results["updated_by[userId]"] = ok
    else:
        print("  SKIP updated_by[userId]: no updater id on baseline")
        results["updated_by[userId]"] = "SKIP (no updater id)"

    if updated_by_name_hits is not None and updated_by_id_hits is not None:
        comparison = compare_result_ids(
            "updated_by",
            name_hits=updated_by_name_hits,
            id_hits=updated_by_id_hits,
            baseline_id=baseline_id,
        )
        print(f"  updated_by result parity: {comparison}")
        results["updated_by[same items]"] = comparison

    ALL_RESULTS["inventory"] = results


section("inventory GET search")
inv_hits = list(
    client.inventory.search(
        category=[InventoryCategory.RAW_MATERIALS],
        max_items=3,
    )
)
show_count("inventory category filter", inv_hits)

section("inventory POST metadata_filters")
try:
    meta_hits = list(
        client.inventory.search(
            category=[InventoryCategory.RAW_MATERIALS],
            metadata_filters={"apurv_inventory_2": {"name": ["Liquid"]}},
            max_items=3,
        )
    )
    show_count("inventory metadata_filters", meta_hits)
except Exception as exc:
    print(f"inventory metadata_filters failed: {exc}")

section("tasks search with date filters")
try:
    task_hits = list(
        client.tasks.search(
            from_created_at="2020-01-01",
            to_created_at="2030-12-31",
            max_items=3,
        )
    )
    show_count("tasks date filters", task_hits)
except Exception as exc:
    print(f"tasks date filters failed: {exc}")

section("data_templates search")
try:
    dt_hits = list(client.data_templates.search(max_items=3))
    show_count("data_templates", dt_hits)
    if dt_hits and hasattr(dt_hits[0], "description"):
        print(f"  description field present: {dt_hits[0].description!r}")
except Exception as exc:
    print(f"data_templates search failed: {exc}")

section("parameter_groups search")
try:
    pg_hits = list(client.parameter_groups.search(max_items=3))
    show_count("parameter_groups", pg_hits)
except Exception as exc:
    print(f"parameter_groups search failed: {exc}")

section("projects search with update filters")
try:
    proj_hits = list(
        client.projects.search(
            from_updated_at="2020-01-01",
            to_updated_at="2030-12-31",
            max_items=3,
        )
    )
    show_count("projects update date filters", proj_hits)
    if proj_hits:
        hit = proj_hits[0]
        print(f"  application: {getattr(hit, 'application', None)}")
        print(f"  technology: {getattr(hit, 'technology', None)}")
except Exception as exc:
    print(f"projects search failed: {exc}")

section("property_data search with update filters")
try:
    pd_hits = list(
        client.property_data.search(
            from_updated_at="2020-01-01",
            to_updated_at="2030-12-31",
            max_items=3,
        )
    )
    show_count("property_data update date filters", pd_hits)
except Exception as exc:
    print(f"property_data search failed: {exc}")

section("btinsights search baseline")
try:
    bt_hits = list(client.btinsights.search(max_items=3))
    show_count("btinsights baseline", bt_hits)
except Exception as exc:
    print(f"btinsights search failed: {exc}")

section("created_by / updated_by filter smoke tests")
test_inventory_user_filters()
test_str_user_filters(
    "tasks",
    baseline_fn=lambda: next(iter(client.tasks.search(max_items=1)), None),
    search_fn=client.tasks.search,
    hydrate=lambda hit: hit.hydrate(),
)
test_str_user_filters(
    "data_templates",
    baseline_fn=lambda: next(iter(client.data_templates.search(max_items=1)), None),
    search_fn=client.data_templates.search,
)
test_str_user_filters(
    "parameter_groups",
    baseline_fn=lambda: next(iter(client.parameter_groups.search(max_items=1)), None),
    search_fn=client.parameter_groups.search,
)
test_str_user_filters(
    "projects",
    baseline_fn=lambda: next(iter(client.projects.search(max_items=1)), None),
    search_fn=client.projects.search,
    hydrate=lambda hit: hit.hydrate(),
)
test_str_user_filters(
    "property_data",
    baseline_fn=lambda: next(iter(client.property_data.search(max_items=1)), None),
    search_fn=client.property_data.search,
    created_by_user_id_only=True,
)
test_str_user_filters(
    "btinsights",
    baseline_fn=lambda: next(iter(client.btinsights.search(max_items=1)), None),
    search_fn=client.btinsights.search,
    supports_updated=True,
)

section("summary")
for collection, results in ALL_RESULTS.items():
    print(f"\n{collection}:")
    for variant, outcome in results.items():
        if outcome is True:
            status = "PASS"
        elif outcome is False:
            status = "FAIL"
        else:
            status = str(outcome)
        print(f"  {variant}: {status}")

print("\nDone.")
