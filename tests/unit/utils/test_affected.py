from pathlib import Path

import pytest

from tests.utils.affected import (
    HUBS,
    ItemInfo,
    client_attrs,
    collection_attr_map,
    fixture_client_attrs,
    import_closure,
    is_full_run,
    select,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


CLIENT_PY = """
from albert.collections.tags import TagCollection
from albert.collections.chat_sessions import ChatSessionCollection as Chats


class Albert:
    @property
    def tags(self) -> TagCollection:
        return TagCollection(session=self.session)

    @property
    def not_a_collection(self) -> int:
        return 1

    def plain_method(self) -> TagCollection:
        return TagCollection(session=self.session)


class AsyncAlbert:
    @property
    def chat_sessions(self) -> Chats:
        return Chats(session=self.session)
"""


def test_collection_attr_map_covers_both_clients_and_resolves_modules(tmp_path):
    """Test attr map parses both client classes and resolves module paths."""
    _write(
        tmp_path,
        {
            "src/albert/client.py": CLIENT_PY,
            "src/albert/collections/tags.py": "",
            "src/albert/collections/chat_sessions.py": "",
        },
    )

    assert collection_attr_map(tmp_path / "src/albert/client.py") == {
        "tags": "src/albert/collections/tags.py",
        "chat_sessions": "src/albert/collections/chat_sessions.py",
    }


def test_client_attrs_finds_client_and_async_client_only():
    """Test only attribute access on client receivers is reported."""
    source = '''
"""client.docstring_only"""

def test_x(client, async_client, other):
    client.tags.get_all()
    async_client.chat_sessions.create()
    other.inventory.get_all()
    text = "client.in_string"
    return client.session
'''
    assert client_attrs(source) == {"tags", "chat_sessions", "session"}


def test_fixture_client_attrs_handles_decorator_forms_and_async():
    """Test sync and async fixtures in every decorator form are parsed."""
    source = """
import pytest
import pytest_asyncio

@pytest.fixture
def a(client):
    return client.tags

@pytest.fixture(scope="session")
def b(client):
    return client.inventory

@pytest_asyncio.fixture(scope="session")
async def c(async_client):
    return async_client.chat_sessions

@pytest.fixture(name="renamed")
def d(client):
    return client.lots

def not_a_fixture(client):
    return client.users
"""
    assert fixture_client_attrs(source) == {
        "a": {"tags"},
        "b": {"inventory"},
        "c": {"chat_sessions"},
        "renamed": {"lots"},
    }


def _tree(tmp_path: Path, files: dict[str, str]) -> Path:
    _write(tmp_path, files)
    return tmp_path / "src"


def test_import_closure_follows_module_level_and_nested_imports(tmp_path):
    """Test top-level and function-level imports are both followed transitively."""
    src = _tree(
        tmp_path,
        {
            "src/albert/collections/a.py": "from albert.resources.m import Model\n",
            "src/albert/resources/m.py": (
                "def f():\n    from albert.collections.nested import N\n"
            ),
            "src/albert/collections/nested.py": "",
        },
    )

    assert import_closure(
        tmp_path / "src/albert/collections/a.py", src_root=src, hubs=frozenset()
    ) == {
        "src/albert/collections/a.py",
        "src/albert/resources/m.py",
        "src/albert/collections/nested.py",
    }


def test_import_closure_resolves_submodules_and_packages(tmp_path):
    """Test ``from pkg import submodule`` and ``import a.b`` resolve to files."""
    src = _tree(
        tmp_path,
        {
            "src/albert/a.py": "from albert.core import session\nimport albert.pkg\n",
            "src/albert/core/__init__.py": "",
            "src/albert/core/session.py": "",
            "src/albert/pkg/__init__.py": "",
        },
    )

    assert import_closure(tmp_path / "src/albert/a.py", src_root=src, hubs=frozenset()) == {
        "src/albert/a.py",
        "src/albert/core/__init__.py",
        "src/albert/core/session.py",
        "src/albert/pkg/__init__.py",
    }


def test_import_closure_stops_at_hubs_and_ignores_foreign_imports(tmp_path):
    """Test hubs are neither returned nor traversed and non-albert imports are ignored."""
    src = _tree(
        tmp_path,
        {
            "src/albert/a.py": "import os\nimport pydantic\nfrom albert import Albert\n",
            "src/albert/__init__.py": "from albert.hidden import X\n",
            "src/albert/hidden.py": "",
        },
    )

    assert import_closure(
        tmp_path / "src/albert/a.py", src_root=src, hubs=frozenset({"src/albert/__init__.py"})
    ) == {"src/albert/a.py"}


def test_import_closure_handles_cycles(tmp_path):
    """Test mutually importing modules terminate with both present."""
    src = _tree(
        tmp_path,
        {
            "src/albert/a.py": "import albert.b\n",
            "src/albert/b.py": "import albert.a\n",
        },
    )

    assert import_closure(tmp_path / "src/albert/a.py", src_root=src, hubs=frozenset()) == {
        "src/albert/a.py",
        "src/albert/b.py",
    }


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        ({"src/albert/client.py"}, "src/albert/client.py"),
        ({"src/albert/exceptions.py"}, "src/albert/exceptions.py"),
        ({"src/albert/core/session.py"}, "src/albert/core/session.py"),
        ({"src/albert/core/shared/enums.py"}, "src/albert/core/shared/enums.py"),
        ({"src/albert/collections/base.py"}, "src/albert/collections/base.py"),
        ({"tests/integration/conftest.py"}, "tests/integration/conftest.py"),
        ({"tests/integration/utils/helpers.py"}, "tests/integration/utils/helpers.py"),
        ({"tests/utils/affected.py"}, "tests/utils/affected.py"),
        ({"pyproject.toml"}, "pyproject.toml"),
        ({".github/workflows/test.yml"}, ".github/workflows/test.yml"),
        ({"docs/index.md", "src/albert/core/session.py"}, "src/albert/core/session.py"),
        ({"src/albert/collections/tags.py"}, None),
        ({"src/albert/core_extras.py"}, None),
        ({"tests/integration/collections/test_tags.py"}, None),
        (set(), None),
    ],
)
def test_is_full_run(changed, expected):
    """Test exact-file and directory-prefix triggers are detected and others are not."""
    assert is_full_run(changed) == expected


@pytest.fixture
def repo(tmp_path):
    """A small repo: tags and lots collections, a shared resource, four test modules."""
    _write(
        tmp_path,
        {
            "src/albert/__init__.py": "",
            "src/albert/collections/tags.py": "",
            "src/albert/collections/other.py": "",
            "src/albert/collections/lots.py": "from albert.resources.shared import S\n",
            "src/albert/resources/shared.py": "",
            "tests/integration/collections/test_tags.py": "def test_a(client):\n    client.tags\n",
            "tests/integration/collections/test_lots.py": (
                "def test_b(client, seeded_tags):\n    client.lots\n"
            ),
            "tests/integration/collections/test_via_fixture.py": (
                "def test_c(seeded_tags):\n    pass\n"
            ),
            "tests/integration/collections/test_bare.py": "def test_d():\n    pass\n",
            "tests/integration/collections/test_other.py": (
                "def test_e(client, seeded_other):\n    client.other\n"
            ),
        },
    )
    return tmp_path


ATTR_MAP = {
    "tags": "src/albert/collections/tags.py",
    "lots": "src/albert/collections/lots.py",
    "other": "src/albert/collections/other.py",
}
FIXTURE_ATTRS = {"seeded_tags": {"tags"}, "seeded_other": set()}
BASE = "tests/integration/collections/"


def _items() -> list[ItemInfo]:
    return [
        ItemInfo(f"{BASE}test_tags.py::test_a", f"{BASE}test_tags.py", ("client",)),
        ItemInfo(f"{BASE}test_lots.py::test_b", f"{BASE}test_lots.py", ("client", "seeded_tags")),
        ItemInfo(
            f"{BASE}test_via_fixture.py::test_c", f"{BASE}test_via_fixture.py", ("seeded_tags",)
        ),
        ItemInfo(f"{BASE}test_bare.py::test_d", f"{BASE}test_bare.py", ()),
        ItemInfo(
            f"{BASE}test_other.py::test_e", f"{BASE}test_other.py", ("client", "seeded_other")
        ),
    ]


def _run(repo: Path, changed: set[str]) -> tuple[list[str], list[str], str]:
    return select(
        _items(), changed, repo_root=repo, attr_map=ATTR_MAP, fixture_attrs=FIXTURE_ATTRS
    )


def test_select_collection_change_picks_direct_users_and_fixture_dependents(repo):
    """Test a collection change selects its direct users, fixture dependents and the
    unattributable test, and nothing else.
    """
    selected, deselected, reason = _run(repo, {"src/albert/collections/tags.py"})

    assert selected == [
        f"{BASE}test_tags.py::test_a",
        f"{BASE}test_lots.py::test_b",
        f"{BASE}test_via_fixture.py::test_c",
        f"{BASE}test_bare.py::test_d",
    ]
    assert deselected == [f"{BASE}test_other.py::test_e"]
    assert reason == ("4 selected, 1 deselected (changed: src/albert/collections/tags.py)")


def test_select_transitive_import_change_picks_only_importers(repo):
    """Test a resource reached through a collection import selects that collection's users."""
    selected, _, _ = _run(repo, {"src/albert/resources/shared.py"})

    assert selected == [f"{BASE}test_lots.py::test_b", f"{BASE}test_bare.py::test_d"]


def test_select_changed_test_module_is_selected(repo):
    """Test a changed test file selects its own tests."""
    selected, _, _ = _run(repo, {f"{BASE}test_other.py"})

    assert selected == [f"{BASE}test_bare.py::test_d", f"{BASE}test_other.py::test_e"]


def test_select_full_run_trigger_selects_everything(repo):
    """Test a full-run trigger selects every item and names the trigger."""
    selected, deselected, reason = _run(repo, {"src/albert/core/session.py"})

    assert selected == [item.node_id for item in _items()]
    assert deselected == []
    assert reason == "full run (trigger: src/albert/core/session.py)"


def test_select_empty_changed_selects_only_unattributable(repo):
    """Test with nothing changed only tests with no attributable source remain."""
    selected, deselected, _ = _run(repo, set())

    assert selected == [f"{BASE}test_bare.py::test_d"]
    assert len(deselected) == 4


def test_real_repo_attr_map_resolves_to_existing_files():
    """Test the attr map built from the real client covers known attrs and valid files."""
    attr_map = collection_attr_map(REPO_ROOT / "src/albert/client.py")

    assert {"inventory", "tasks", "chat_sessions"} <= attr_map.keys()
    assert [p for p in attr_map.values() if not (REPO_ROOT / p).is_file()] == []


def test_real_repo_hubs_exist():
    """Test the hub paths used to stop traversal point at real files."""
    assert [p for p in HUBS if not (REPO_ROOT / p).is_file()] == []
