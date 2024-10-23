import logging
from collections.abc import Generator, Iterator

from albert.collections.base import BaseCollection
from albert.resources.base import Status
from albert.resources.users import User
from albert.session import AlbertSession


class UserCollection(BaseCollection):
    _api_version = "v3"
    _updatable_attributes = {"name", "status", "email", "metadata"}

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the UserCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{UserCollection._api_version}/users"

    def _list_generator(
        self,
        *,
        text: str | None = None,
        offset: int | None = None,
        limit: int = 50,
        status=None,
        search_fields=None,
    ) -> Generator[User, None, None]:
        params = {"limit": limit}
        if status:
            params["status"] = status
        if text:
            params["text"] = text.lower()
        if offset:  # pragma: no cover
            params["offset"] = offset
        if search_fields:
            params["searchFields"] = search_fields
        while True:
            response = self.session.get(self.base_path + "/search", params=params)
            user_data = response.json().get("Items", [])
            if not user_data or user_data == []:
                break
            for u in user_data:
                # do a full get
                yield self.get_by_id(user_id=u["albertId"])
            offset = response.json().get("offset")
            if not offset or len(user_data) < limit:
                break
            params["offset"] = int(offset) + int(limit)

    def list(
        self, *, text: str | None = None, status: Status = None, search_fields=None
    ) -> Iterator[User]:
        """Lists Users based on criteria

        Parameters
        ----------
        text : Optional[str], optional
            text to search against, by default None

        Returns
        -------
        Generator
            Generator of matching Users or None
        """
        return self._list_generator(text=text, status=status, search_fields=search_fields)

    def get_by_id(self, *, user_id: str) -> User | None:
        """
        Retrieves a User by its ID.

        Parameters
        ----------
        user_id : str
            The ID of the user to retrieve.

        Returns
        -------
        User
            The User object if found, None otherwise.
        """
        url = f"{self.base_path}/{user_id}"
        response = self.session.get(url)
        user = User(**response.json())
        return user

    def create(self, *, user: User) -> User:  # pragma: no cover
        """Create a new User

        Parameters
        ----------
        user : User
            The user to create

        Returns
        -------
        User
            The created User
        """

        hits = self.list(text=user.email)
        for u in hits:
            if u.email == user.email:
                logging.warning(
                    f"User with email {user.email} already exists. Returning existing user."
                )
                return u

        response = self.session.post(
            self.base_path, json=user.model_dump(by_alias=True, exclude_none=True)
        )
        user = User(**response.json())
        return user

    def update(self, *, updated_object: User) -> User:
        # Fetch the current object state from the server or database
        current_object = self.get_by_id(user_id=updated_object.id)

        # Generate the PATCH payload
        patch_payload = self._generate_patch_payload(
            existing=current_object, updated=updated_object
        )

        url = f"{self.base_path}/{updated_object.id}"
        self.session.patch(url, json=patch_payload)

        updated_user = self.get_by_id(user_id=updated_object.id)
        return updated_user
