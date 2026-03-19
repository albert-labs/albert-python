# Teams

Teams in Albert allow organizations to manage groups of Users that can be assigned in bulk to Projects.

## Create a team with members

!!! example "Create a team with an owner and a viewer"
    ```python
    from albert import Albert
    from albert.resources.teams import TeamMember

    client = Albert.from_client_credentials()

    team = client.teams.create(
        name="Formulations",
        members=[
            TeamMember(id="USR123", role="TeamOwner"),
            TeamMember(id="USR456", role="TeamViewer"),
        ],
    )
    print(team.id, team.name)
    ```

## Add members to a team

!!! example "Add new members to an existing team"
    ```python
    from albert import Albert
    from albert.resources.teams import TeamMember

    client = Albert.from_client_credentials()

    team = client.teams.add_users(
        id="TEM1",
        members=[
            TeamMember(id="USR789", role="TeamViewer"),
            TeamMember(id="USR101", role="TeamOwner"),
        ],
    )
    for m in team.members:
        print(m.id, m.name, m.role)
    ```

## Remove members from a team

!!! example "Remove members by user ID"
    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    team = client.teams.remove_users(
        id="TEM1",
        users=["USR789", "USR101"],
    )
    for m in team.members:
        print(m.id, m.name, m.role)
    ```
