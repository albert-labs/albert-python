"""Project document search returns a project's documents only to users who may open it
(PLSV-827).

Runs against long-lived projects (``static_docs.py``) so the documents are already
indexed. Each check runs scoped to the project (``linked``), as a text search for the
file name (``title``), and as a text search for words inside a file (``content``), the
ways a document surfaces in someone's search results.
"""

import pytest

from tests.acl.checks import admin_control, check
from tests.acl.contract.fgc import AccessClass, ReadPath, class_expect
from tests.acl.contract.model import Expect, Verb
from tests.acl.http import Response, call
from tests.acl.static_docs import StaticDoc, ensure_static_doc
from tests.acl.world import PROJECT_CLASSES, grant, revoke
from tests.utils.wait import poll_until

PATH = "/api/v3/projects/documentsearch"
PROPAGATION_S = 90.0


@pytest.fixture(scope="module")
def static_docs(admin) -> dict[AccessClass, StaticDoc]:
    return {cls: ensure_static_doc(admin, cls) for cls in PROJECT_CLASSES}


# mode -> (query params, token that marks the document in the results). The index keys
# documents by the project id without its ``PRO`` prefix. A content search matches the
# text file's body token, which no file name contains, so the hit is marked by file name.
MODES = {
    "linked": (lambda d: {"linkedTo": d.project_id.removeprefix("PRO")}, lambda d: d.canary),
    "title": (lambda d: {"text": d.canary}, lambda d: d.canary),
    "content": (lambda d: {"text": d.content_token}, lambda d: d.content_file),
}
mode_param = pytest.mark.parametrize("mode", list(MODES))


def _search(client, doc: StaticDoc, mode: str) -> Response:
    return call(client, "GET", PATH, params=MODES[mode][0](doc))


def _token(doc: StaticDoc, mode: str) -> str:
    return MODES[mode][1](doc)


def _admin_sees(admin, doc: StaticDoc, mode: str) -> None:
    resp = poll_until(
        lambda: [_search(admin, doc, mode)],
        predicate=lambda r: 200 <= r[0].status < 300 and r[0].contains(_token(doc, mode)),
        timeout=30,
        interval=5,
    )[0]
    if not (200 <= resp.status < 300 and resp.contains(_token(doc, mode))):
        pytest.fail(
            f"harness error: static document {_token(doc, mode)} on {doc.project_id} is not "
            f"in the document-search index for {mode} search yet; rerun later",
            pytrace=False,
        )


@mode_param
@pytest.mark.parametrize(
    "cls", [AccessClass.PRIVATE, AccessClass.CONFIDENTIAL], ids=lambda c: c.value
)
def test_member_sees_project_document(request, admin, switcher, user_ids, static_docs, cls, mode):
    """Test that a project member finds the project's document in document search."""
    doc = static_docs[cls]
    _admin_sees(admin, doc, mode)
    member = switcher.use("docsearch-member", ["ProjectsViewAccess"])
    grant(admin, doc.project_id, user_ids["userA"], "ProjectViewer")
    try:
        resp = poll_until(
            lambda: [_search(member, doc, mode)],
            predicate=lambda r: 200 <= r[0].status < 300 and r[0].contains(_token(doc, mode)),
            timeout=PROPAGATION_S,
            interval=5,
        )[0]
        check(
            request,
            scenario="PLSV-827:document_search",
            subject="member(ProjectViewer)",
            action=f"project[{cls.value}].document_search[{mode}]",
            expect=Expect.ALLOW,
            resp=resp,
            canary=_token(doc, mode),
        )
    finally:
        revoke(admin, doc.project_id, user_ids["userA"])


@mode_param
@pytest.mark.parametrize("cls", PROJECT_CLASSES, ids=lambda c: c.value)
def test_non_member_document_visibility(request, admin, user_b, static_docs, cls, mode):
    """Test that a non-member finds a project's document only when the project is shared."""
    doc = static_docs[cls]
    _admin_sees(admin, doc, mode)
    check(
        request,
        scenario="PLSV-827:document_search",
        subject="non-member",
        action=f"project[{cls.value}].document_search[{mode}]",
        expect=class_expect(cls, Verb.READ, ReadPath.DOCUMENT_SEARCH),
        resp=_search(user_b, doc, mode),
        canary=_token(doc, mode),
    )


def _attachment_ids(resp: Response) -> list[str]:
    """Attachment ids in document-search hits. Hits key attachments as ``ATT...`` or
    ``<project>#<note>#ATT...``; notebook image blocks carry no attachment id."""
    ids = []
    for hit in resp.items():
        last = str(hit.get("albertId", "")).split("#")[-1]
        if last.startswith("ATT"):
            ids.append(last)
    return ids


@pytest.mark.parametrize(
    "cls", [AccessClass.PRIVATE, AccessClass.CONFIDENTIAL], ids=lambda c: c.value
)
def test_non_member_cannot_download_found_documents(request, admin, user_b, static_docs, cls):
    """Test that a non-member cannot download any attachment they find by title or content
    search (PLSV-827: unfiltered search hits plus an attachment fetch that skips the parent)."""
    doc = static_docs[cls]
    found = []
    for mode in ("title", "content"):
        _admin_sees(admin, doc, mode)
        found += _attachment_ids(_search(user_b, doc, mode))
    leaks = []
    for aid in dict.fromkeys(found):
        path = f"/api/v3/attachments/{aid}"
        admin_control(call(admin, "GET", path), f"attachment {aid}.read", canary="signedURL")
        try:
            check(
                request,
                scenario="PLSV-827:document_download",
                subject="non-member",
                action=f"project[{cls.value}].attachment[{aid}].download",
                expect=Expect.DENY,
                resp=call(user_b, "GET", path),
                canary="signedURL",
            )
        except AssertionError as err:
            leaks.append(str(err))
    assert not leaks, "\n".join(leaks)


@mode_param
@pytest.mark.parametrize("cls", PROJECT_CLASSES, ids=lambda c: c.value)
def test_no_project_view_policy_hides_documents(request, admin, switcher, static_docs, cls, mode):
    """Test that a user without Projects view access never finds a project's document,
    whatever the project's class."""
    doc = static_docs[cls]
    _admin_sees(admin, doc, mode)
    user = switcher.use("docsearch-no-projects", ["InventoryViewAccess"])
    check(
        request,
        scenario="PLSV-827:document_search",
        subject="InventoryViewAccess",
        action=f"project[{cls.value}].document_search[{mode}]",
        expect=Expect.DENY,
        resp=_search(user, doc, mode),
        canary=_token(doc, mode),
    )
