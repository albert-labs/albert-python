from collections.abc import Generator

from albert.albert import Albert
from albert.resources.teams import Team


def test_create_and_delete(client: Albert, seeded_teams: list[Team]):
    # get frist team from seeding list
    t = seeded_teams[0]
    # create
    ret_c = client.teams.create(team=t)
    # assert
    assert isinstance(ret_c, Team)
    # delete
    ret_d = client.teams.delete(team_id=ret_c.t)
    # assert
    assert ret_d == True


def test_list(client: Albert):
    # get team
    t = next(client.teams.list())
    # check type
    assert isinstance(t, Team)
