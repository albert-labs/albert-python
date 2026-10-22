from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.patch import PatchDatum


class LocalizationLanguage(str, Enum):
    """A language that localizations can be written in.

    Attributes
    ----------
    GERMAN : str
        German (``"de"``).
    JAPANESE : str
        Japanese (``"ja"``).
    CHINESE : str
        Chinese (``"zh"``).
    SPANISH : str
        Spanish (``"es"``).
    """

    GERMAN = "de"
    JAPANESE = "ja"
    CHINESE = "zh"
    SPANISH = "es"


class LocalizationEnumValue(BaseAlbertModel):
    """An enum option within a localization validation rule, with its own translations."""

    id: str | None = Field(default=None)
    """The ID of the enum value (format ``ENM...``)."""

    text: str | None = Field(default=None)
    """The source (untranslated) display text of the enum value."""

    localization: dict[str, dict[str, str]] | None = Field(default=None)
    """Translations keyed by attribute and language code (e.g. ``{"text": {"de": "Apfel"}}``). Language codes are drawn from [`LocalizationLanguage`][albert.resources.localizations.LocalizationLanguage]."""


class LocalizationValidation(BaseAlbertModel):
    """A validation rule on a localized field.

    Enum rules carry the allowed options in ``value``, and each option can carry
    translations of its display text.
    """

    datatype: str | None = Field(default=None)
    """The data type the rule applies to (e.g. ``"enum"``, ``"number"``)."""

    value: list[LocalizationEnumValue] | str | int | float | bool | None = Field(default=None)
    """For enum rules, the list of allowed options; otherwise the bound for ``operator``."""

    operator: str | None = Field(default=None)
    """The comparison operator for bound rules (e.g. ``"lt"``)."""


class Localization(BaseAlbertModel):
    """Translations for an entity or one of its child records in the Albert platform.

    A single entity (e.g. a data template) produces one [`Localization`][albert.resources.localizations.Localization]
    for the entity itself plus one per localizable child record (data columns,
    parameters). Managed through
    [`LocalizationCollection`][albert.collections.localizations.LocalizationCollection]
    (``client.localizations``).

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        rows = client.localizations.get_by_id(id="DAT1")
        for row in rows:
            print(row.unique_id, row.localization)
        ```
    """

    id: str | None = Field(default=None, alias="albertId")
    """The Albert ID of the localized entity (e.g. ``"DAT1"``)."""

    name: str | None = Field(default=None)
    """The source (untranslated) name of the entity or child record."""

    unique_id: str | None = Field(default=None, alias="uniqueId")
    """Identifies the record the translations apply to: the module name for the main entity (e.g. ``"DAT"``), or ``"<childId>#<position>"`` for a child record (e.g. ``"DAC1#COL0"``, ``"PRM1#ROW1"``)."""

    description: str | None = Field(default=None)
    """The source (untranslated) description of the entity."""

    localization: dict[str, dict[str, str]] | None = Field(default=None)
    """Translations keyed by attribute and language code (e.g. ``{"name": {"de": "Datenvorlage"}}``). Language codes are drawn from [`LocalizationLanguage`][albert.resources.localizations.LocalizationLanguage]."""

    validation: list[LocalizationValidation] | None = Field(default=None)
    """Validation rules on the field. Enum rules carry translations of the allowed options."""

    type: str | None = Field(default=None)
    """The data type of the attribute (e.g. ``"string"``, ``"enum"``, ``"number"``)."""

    hidden: bool | None = Field(default=None)
    """Whether the field is hidden."""

    module: str | None = Field(default=None)
    """The module the record belongs to (e.g. ``"DAT"``, ``"DAC"``, ``"PRM"``)."""

    required: bool | None = Field(default=None)
    """Whether the field is required."""


class LocalizationPatchDatum(PatchDatum):
    """A single translation change for an entity or child record.

    ``operation`` is ``"add"`` to create a translation, ``"update"`` to change an
    existing one (``old_value`` must match), and ``"delete"`` to remove one.
    """

    language: LocalizationLanguage | str = Field(min_length=1, max_length=255)
    """The language the translation applies to. Use a [`LocalizationLanguage`][albert.resources.localizations.LocalizationLanguage] member (e.g. ``LocalizationLanguage.GERMAN``) or its language code (``"de"``); plain strings keep languages not yet in the enum usable."""

    unique_id: str = Field(alias="uniqueId", min_length=1, max_length=255)
    """The record the translation applies to: the module name for the main entity (e.g. ``"DAT"``), or ``"<childId>#<position>"`` for a child record."""
