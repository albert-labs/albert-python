from albert.collections.lots import LotCollection
from albert.collections.teams import TeamCollection
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.resources.lots import Lot
from albert.resources.teams import Team, TeamMember


def test_exclude_unset_default():
    payload = PatchPayload(
        data=[
            PatchDatum(
                attribute="test",
                operation=PatchOperation.UPDATE,
                new_value=4,
                old_value=None,
            ),
            PatchDatum(
                attribute="test",
                operation=PatchOperation.UPDATE,
                new_value=4,
            ),
        ]
    )
    dumped = payload.model_dump(mode="json", by_alias=True)

    datum0 = dumped["data"][0]
    assert datum0["oldValue"] is None
    assert datum0["newValue"] == 4

    datum1 = dumped["data"][1]
    assert "oldValue" not in datum1
    assert datum1["newValue"] == 4


def test_lots_patch_payload_stringifies_numeric_values():
    """Test that lot cost and initialQuantity patch values are serialized as decimal strings."""
    existing = Lot(
        id="LOT1",
        inventory_id="INV1",
        inventory_on_hand=10.0,
        cost=50.0,
        initial_quantity=100.0,
    )
    updated = existing.model_copy(update={"cost": 42.5, "initial_quantity": 200.0})

    payload = LotCollection(session=None)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )
    by_attribute = {d.attribute: d for d in payload.data}

    assert by_attribute["cost"].operation == PatchOperation.UPDATE
    assert by_attribute["cost"].old_value == "50"
    assert by_attribute["cost"].new_value == "42.5"
    assert by_attribute["initialQuantity"].operation == PatchOperation.UPDATE
    assert by_attribute["initialQuantity"].old_value == "100"
    assert by_attribute["initialQuantity"].new_value == "200"


def test_teams_patch_payloads_split_per_member():
    """Test multi-member updates split into one request per member op."""
    current = Team(
        name="Coatings",
        members=[
            TeamMember(id="USR1", role="TeamOwner"),
            TeamMember(id="USR2", role="TeamViewer"),
        ],
    )
    updated = Team(
        name="Coatings R&D",
        members=[
            TeamMember(id="USR1", role="TeamViewer"),  # role change
            TeamMember(id="USR3", role="TeamOwner"),  # added
            TeamMember(id="USR4"),  # added, defaults to TeamViewer
        ],
    )

    payloads = TeamCollection._generate_patch_payloads(current=current, updated=updated)

    # One batched request (name + role change), then one request per member add/remove.
    assert len(payloads) == 4

    batched, *member_payloads = payloads
    assert {op["attribute"] for op in batched} == {"name", "fgc"}

    # The API rejects more than one op per attribute in a call, so each member
    # add/remove op must be sent on its own.
    for payload in member_payloads:
        assert len(payload) == 1
        assert payload[0]["attribute"] == "ACL"

    add_ops = [p[0] for p in member_payloads if p[0]["operation"] == "add"]
    delete_ops = [p[0] for p in member_payloads if p[0]["operation"] == "delete"]
    assert sorted(op["newValue"][0]["id"] for op in add_ops) == ["USR3", "USR4"]
    assert {tuple(op["newValue"][0].items()) for op in add_ops} == {
        (("id", "USR3"), ("fgc", "TeamOwner")),
        (("id", "USR4"), ("fgc", "TeamViewer")),
    }
    assert [op["oldValue"] for op in delete_ops] == [[{"id": "USR2"}]]


def test_teams_patch_payloads_single_member_stays_batched():
    """Test a name change plus one member op split into exactly two requests."""
    current = Team(name="Coatings", members=[TeamMember(id="USR1", role="TeamOwner")])
    updated = Team(
        name="Coatings R&D",
        members=[
            TeamMember(id="USR1", role="TeamOwner"),
            TeamMember(id="USR2", role="TeamViewer"),
        ],
    )

    payloads = TeamCollection._generate_patch_payloads(current=current, updated=updated)

    assert payloads == [
        [
            {
                "operation": "update",
                "attribute": "name",
                "oldValue": "Coatings",
                "newValue": "Coatings R&D",
            }
        ],
        [
            {
                "operation": "add",
                "attribute": "ACL",
                "newValue": [{"id": "USR2", "fgc": "TeamViewer"}],
            }
        ],
    ]


def test_teams_patch_payloads_no_changes():
    """Test no patch requests are built when nothing changed."""
    team = Team(name="Coatings", members=[TeamMember(id="USR1", role="TeamOwner")])
    assert TeamCollection._generate_patch_payloads(current=team, updated=team) == []
