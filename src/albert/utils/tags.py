from albert.collections.tags import TagCollection
from albert.core.session import AlbertSession
from albert.resources.tags import Tag


def unique_tags(tags: list[Tag]) -> list[Tag]:
    """Return the tags with duplicates removed, keeping first-seen order.

    Tags with an ID are matched by ID. Tags without one are matched by name,
    ignoring case, because the tags API treats names case-insensitively.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[Tag] = []
    for tag in tags:
        key = ("id", tag.id) if tag.id else ("name", tag.tag.casefold())
        if key in seen:
            continue
        seen.add(key)
        unique.append(tag)
    return unique


def resolve_tags(*, session: AlbertSession, tags: list[Tag]) -> list[Tag]:
    """Return the tags as saved Tags, creating any that do not exist yet.

    Duplicates are removed before and after lookup, so each unique tag
    triggers at most one get_or_create call.
    """
    tag_collection = TagCollection(session=session)
    resolved = [
        tag_collection.get_or_create(tag=t) if t.id is None else t for t in unique_tags(tags)
    ]
    # A name-only tag can resolve to the same ID as a tag passed with an ID.
    return unique_tags(resolved)
