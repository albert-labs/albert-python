from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import SecurityClass
from albert.core.shared.identifiers import InventoryId
from albert.core.shared.models.base import AuditFields
from albert.core.shared.types import MetadataItem, SerializeAsEntityLink
from albert.resources._mixins import HydrationMixin
from albert.resources.acls import ACL
from albert.resources.cas import Cas
from albert.resources.companies import Company
from albert.resources.lists import ListItem
from albert.resources.locations import Location
from albert.resources.tagged_base import BaseTaggedResource
from albert.resources.tags import Tag


class InventoryMergeModule(str, Enum):
    """
    A data category that can be carried over when merging inventory items.

    When duplicate inventory items are merged (see [`MergeInventory`][albert.resources.inventory.MergeInventory] and
    [`merge`][albert.collections.inventory.InventoryCollection.merge]), each selected
    module names a body of data to fold from the child item(s) into the surviving
    parent item. When no modules are specified, all modules are included.

    Attributes
    ----------
    PRICING : str
        Pricing data.
    NOTES : str
        Notes.
    SDS : str
        Safety Data Sheets.
    PD : str
        Product Design: worksheet column references for this inventory item.
    BD : str
        Batch data.
    LOT : str
        Lot data.
    CAS : str
        CAS numbers.
    TAS : str
        Tasks.
    WFL : str
        Workflows.
    PRG : str
        Parameter groups.
    PTD : str
        Property data.
    """

    PRICING = "PRICING"
    NOTES = "NOTES"
    SDS = "SDS"
    PD = "PD"
    BD = "BD"
    LOT = "LOT"
    CAS = "CAS"
    TAS = "TAS"
    WFL = "WFL"
    PRG = "PRG"
    PTD = "PTD"


ALL_MERGE_MODULES: list[InventoryMergeModule] = list(InventoryMergeModule)
"""All modules selectable for inventory merge."""


class InventoryCategory(str, Enum):
    """The kind of material an [`InventoryItem`][albert.resources.inventory.InventoryItem] represents.

    Every inventory item belongs to exactly one category, which determines how it
    is used across the platform and which fields are relevant to it.

    Attributes
    ----------
    RAW_MATERIALS : str
        A purchased substance used as an ingredient (e.g. a solvent or pigment).
        Typically linked to a manufacturing ``company`` and one or more CAS numbers.
    CONSUMABLES : str
        Lab supplies consumed during work (e.g. gloves, vials, filters).
    EQUIPMENT : str
        Instruments and apparatus (e.g. a balance or spectrometer).
    FORMULAS : str
        A mixture designed in Albert through a Worksheet. Formulas are not created
        through the inventory collection; they are produced by the Worksheet
        collection ([`WorksheetCollection`][albert.collections.worksheets.WorksheetCollection]).
    """

    RAW_MATERIALS = "RawMaterials"
    CONSUMABLES = "Consumables"
    EQUIPMENT = "Equipment"
    FORMULAS = "Formulas"


class InventoryUnitCategory(str, Enum):
    """The dimension of the unit an [`InventoryItem`][albert.resources.inventory.InventoryItem] is measured and stocked in.

    Determines how quantities on hand and in formulas are interpreted. When not
    supplied, the category defaults based on [`InventoryCategory`][albert.resources.inventory.InventoryCategory]: ``MASS``
    for raw materials and formulas, ``UNITS`` for equipment and consumables.

    Attributes
    ----------
    MASS : str
        Measured by mass (e.g. grams, kilograms).
    VOLUME : str
        Measured by volume (e.g. milliliters, liters).
    LENGTH : str
        Measured by length (e.g. meters).
    PRESSURE : str
        Measured by pressure.
    UNITS : str
        Counted as discrete units (e.g. each item).
    """

    MASS = "mass"
    VOLUME = "volume"
    LENGTH = "length"
    PRESSURE = "pressure"
    UNITS = "units"


class CasAuditFieldsWithEmail(AuditFields):
    """The audit fields for a CAS resource with email"""

    email: str | None = Field(default=None)


class CasAmount(BaseAlbertModel):
    """A single CAS constituent and its concentration within an [`InventoryItem`][albert.resources.inventory.InventoryItem].

    A ``CasAmount`` links one CAS number (a chemical substance identifier) to the
    amount of that substance present in an inventory item, expressed as a range
    (``min`` to ``max``) with an optional ``target``. A list of these on an
    [`InventoryItem`][albert.resources.inventory.InventoryItem] gives the item's compositional breakdown.

    Identify the CAS in one of two ways: pass a full [`Cas`][albert.resources.cas.Cas]
    object as ``cas`` (its ``id``, ``number``, and ``cas_smiles`` are then copied onto
    this amount), or pass just the CAS resource ``id`` string. Do not pass both.

    !!! example
        ```python
        from albert.resources.inventory import CasAmount

        # Reference an existing CAS resource by its Albert ID, 10-30% concentration
        amount = CasAmount(min=10.0, max=30.0, id="CAS1")
        ```

    Attributes
    ----------
    min : float
        The minimum amount (concentration) of the CAS in the item.
    max : float
        The maximum amount (concentration) of the CAS in the item.
    target : float | None
        The target amount of the CAS in the item. Serialized as ``inventoryValue``.
    id : str | None
        The Albert ID of the CAS resource this amount represents. Provide either a
        ``cas`` object or an ``id``; when ``cas`` is given, this is set from it.
    cas_category : str | None
        Whether the CAS is a trade secret.
    inventory_function : list[ListItem | str] | None
        Business-controlled functions associated with the CAS in this inventory
        context (e.g. what role the substance plays). Values come from a managed list.
    type : str | None
        The CAS type. Can be retrieved from the CAS collection before construction.
    classification_type : str | None
        The EU classification source for the CAS: harmonized, notified, or REACH.
    cas : Cas | None
        The full CAS object associated with this amount. Read-only after init; excluded
        from serialization. Provide either a ``cas`` or an ``id``.
    cas_smiles : str | None
        The SMILES string of the CAS resource. Read-only; set from the ``cas`` object.
    number : str | None
        The CAS number (e.g. ``"7440-32-6"``). Read-only; set from the ``cas`` object.
    created : AuditFields | None
        Audit metadata for creation. Read-only.
    updated : CasAuditFieldsWithEmail | None
        Audit metadata for the last update. Read-only.

    See Also
    --------
    albert.resources.cas.Cas : The CAS resource referenced by this amount.
    InventoryItem : Holds the list of ``CasAmount`` entries for an item.
    """

    min: float
    max: float
    target: float | None = Field(default=None, alias="inventoryValue")
    id: str | None = Field(default=None)
    cas_category: str | None = Field(default=None, alias="casCategory")
    inventory_function: list[SerializeAsEntityLink[ListItem] | str] | None = Field(
        default=None, alias="inventoryFunction"
    )
    type: str | None = Field(default=None)
    classification_type: str | None = Field(default=None, alias="classificationType")

    # Read-only fields
    cas: Cas | None = Field(default=None, exclude=True)
    cas_smiles: str | None = Field(default=None, alias="casSmiles", exclude=True, frozen=True)
    number: str | None = Field(default=None, exclude=True, frozen=True)
    created: AuditFields | None = Field(
        default=None,
        alias="Created",
        frozen=True,
    )
    updated: CasAuditFieldsWithEmail | None = Field(
        default=None,
        alias="Updated",
        frozen=True,
    )

    @model_validator(mode="after")
    def set_cas_attributes(self: CasAmount) -> CasAmount:
        """Set attributes after model initialization from the Cas object, if provided."""
        if self.cas is not None:
            object.__setattr__(self, "id", self.cas.id)
            object.__setattr__(self, "cas_smiles", self.cas.smiles)
            object.__setattr__(self, "number", self.cas.number)
        return self


class InventoryMinimum(BaseAlbertModel):
    """A reorder threshold: the minimum stock of an [`InventoryItem`][albert.resources.inventory.InventoryItem] to keep at a Location.

    Each entry pairs one Location with the minimum quantity of an item that must be
    kept on hand there. An [`InventoryItem`][albert.resources.inventory.InventoryItem] may carry several of these, one per
    Location. Identify the Location either by passing a full
    [`Location`][albert.resources.locations.Location] object as ``location`` (its ``id`` is
    then copied onto ``id``), or by passing the location ``id`` string directly. Provide
    one or the other, not both.

    !!! example
        ```python
        from albert.resources.inventory import InventoryMinimum

        minimum = InventoryMinimum(id="LOC1", minimum=500)
        ```

    Attributes
    ----------
    id : str | None
        The Albert ID of the Location this minimum applies to. Provide either a
        ``location`` or an ``id``; when ``location`` is given, this is set from it.
    location : Location | None
        The Location object this minimum applies to. Excluded from serialization.
        Provide either a ``location`` or an ``id``.
    minimum : float
        The minimum amount of the item that must be kept in stock at the Location.
        Must be between 0 and 1e15.

    See Also
    --------
    albert.resources.locations.Location : The Location referenced by this minimum.
    InventoryItem : Holds the list of ``InventoryMinimum`` entries for an item.
    """

    id: str | None = Field(default=None)
    location: Location | None = Field(exclude=True, default=None)
    minimum: float = Field(ge=0, le=1000000000000000)

    @model_validator(mode="after")
    def check_id_or_location(self: InventoryMinimum) -> InventoryMinimum:
        """
        Ensure that either an id or a location is provided.
        """
        if self.id is None and self.location is None:
            raise ValueError(
                "Either an id or a location must be provided for an InventoryMinimum."
            )
        if self.id and self.location and self.location.id != self.id:
            raise ValueError(
                "Only an id or a location can be provided for an InventoryMinimum, not both."
            )

        elif self.location:
            # Avoid recursion by setting the attribute directly
            object.__setattr__(self, "id", self.location.id)
            object.__setattr__(self, "name", self.location.name)

        return self


class InventoryItem(BaseTaggedResource):
    """A catalog entry for a material tracked in Albert.

    An ``InventoryItem`` is the canonical record for a raw material, consumable,
    piece of equipment, or formula. Its [`InventoryCategory`][albert.resources.inventory.InventoryCategory] determines how it
    is used across the platform, and once saved it is referenced everywhere by its
    Inventory ID (format ``INV...``, e.g. ``"INVA1"``). Raw materials are typically
    linked to a manufacturing ``company`` and a compositional breakdown of CAS
    amounts. Formula items are designed in Worksheets rather than created here (the
    [`create`][albert.collections.inventory.InventoryCollection.create] method rejects
    Formula items), and a Formula requires a ``project_id``.

    Items are managed through
    [`InventoryCollection`][albert.collections.inventory.InventoryCollection] (``client.inventory``).

    !!! example
        ```python
        from albert.resources.inventory import InventoryItem, InventoryCategory

        item = InventoryItem(
            name="Titanium Dioxide",
            category=InventoryCategory.RAW_MATERIALS,
            company="Acme Chemicals",
        )
        ```

    Attributes
    ----------
    name : str | None
        The name of the item.
    id : str | None
        The Albert Inventory ID (format ``INV...``). Set when the item is retrieved
        from or created in Albert. Serialized as ``albertId``.
    description : str | None
        A free-text description of the item.
    category : InventoryCategory
        The kind of material this item represents. Required. One of ``RawMaterials``,
        ``Consumables``, ``Equipment``, or ``Formulas``.
    unit_category : InventoryUnitCategory | None
        The dimension the item is measured in (mass, volume, length, pressure, or
        units). If not supplied, it defaults from ``category``: mass for raw materials
        and formulas, units for equipment and consumables.
    security_class : SecurityClass | None
        The access/security class of the item (e.g. confidential, shared, restricted).
    company : Company | str | None
        The manufacturing Company associated with the item (links to the Company
        collection). Accepts a [`Company`][albert.resources.companies.Company] or a name
        string; a string is turned into a Company that is first-or-created on save.
    minimum : list[InventoryMinimum] | None
        Per-Location reorder thresholds for the item. See [`InventoryMinimum`][albert.resources.inventory.InventoryMinimum].
    alias : str | None
        An alternate name for the item.
    cas : list[CasAmount] | None
        The item's compositional breakdown as CAS amounts. See [`CasAmount`][albert.resources.inventory.CasAmount].
    is_formula_override : bool | None
        Whether the substance/CAS-level breakdown for this formula has been overridden
        from the auto-calculated value; commonly set to indicate the formula is not a
        non-reactive homogeneous mixture.
    metadata : dict[str, MetadataItem] | None
        Custom metadata fields. Allowed keys are defined by the workspace's
        CustomFields configuration.
    project_id : str | None
        The parent Project ID. Required for Formulas. Serialized as ``parentId``.
    acls : list[ACL]
        Access-control entries governing who can act on the item.
    tags : list[Tag | str] | None
        Tags on the item. A string is turned into a Tag that is first-or-created.
        Inherited from [`BaseTaggedResource`][albert.resources.tagged_base.BaseTaggedResource].
    inventory_on_hand : float
        Total amount currently on hand across all lots. Read-only.
    formula_id : str | None
        The formula ID for a formula item. Read-only.
    un_number : str | None
        The UN hazardous-material number, when applicable. Read-only.
    task_config : list[dict] | None
        Task configuration associated with the item. Read-only.
    symbols : list[dict] | None
        Hazard/pictogram symbols associated with the item. Read-only.
    recent_atachment_id : str | None
        The ID of the most recent attachment on the item. Read-only.

    See Also
    --------
    albert.collections.inventory.InventoryCollection : Create, search, and manage items.
    InventoryCategory : The set of allowed categories.
    CasAmount : Compositional entries used in ``cas``.
    InventoryMinimum : Per-Location reorder thresholds used in ``minimum``.
    InventorySpec : Declared property specifications for an item.
    """

    name: str | None = None
    id: str | None = Field(None, alias="albertId")
    description: str | None = None
    category: InventoryCategory
    unit_category: InventoryUnitCategory | None = Field(default=None, alias="unitCategory")
    security_class: SecurityClass | None = Field(default=None, alias="class")
    company: SerializeAsEntityLink[Company] | None = Field(default=None, alias="Company")
    minimum: list[InventoryMinimum] | None = Field(default=None)  # To do
    alias: str | None = Field(default=None)
    cas: list[CasAmount] | None = Field(default=None, alias="Cas")
    is_formula_override: bool | None = Field(default=None, alias="isFormulaOverride")
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)
    project_id: str | None = Field(default=None, alias="parentId")
    acls: list[ACL] = Field(default_factory=list, alias="ACL")

    # Read-only fields
    inventory_on_hand: float = Field(default=0.0, alias="onHand", exclude=True, frozen=True)
    task_config: list[dict] | None = Field(
        default=None, alias="TaskConfig", exclude=True, frozen=True
    )
    formula_id: str | None = Field(default=None, alias="formulaId", exclude=True, frozen=True)
    symbols: list[dict] | None = Field(default=None, alias="Symbols", exclude=True, frozen=True)
    un_number: str | None = Field(default=None, alias="unNumber", exclude=True, frozen=True)
    recent_atachment_id: str | None = Field(
        default=None, alias="recentAttachmentId", exclude=True, frozen=True
    )

    @field_validator("company", mode="before")
    @classmethod
    def validate_company_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = Company(name=value)
        return value

    @field_validator("un_number", mode="before")
    @classmethod
    def validate_un_number(cls, value: Any) -> Any:
        if value == "N/A":
            value = None
        return value

    @model_validator(mode="after")
    def set_unit_category(self) -> InventoryItem:
        """Set unit category from category if not defined."""
        if self.unit_category is None:
            if self.category in [InventoryCategory.RAW_MATERIALS, InventoryCategory.FORMULAS]:
                object.__setattr__(self, "unit_category", InventoryUnitCategory.MASS)
            elif self.category in [InventoryCategory.EQUIPMENT, InventoryCategory.CONSUMABLES]:
                object.__setattr__(self, "unit_category", InventoryUnitCategory.UNITS)
        return self

    @model_validator(mode="after")
    def validate_formula_fields(self) -> InventoryItem:
        """Ensure required fields are present for formulas."""
        if self.category == InventoryCategory.FORMULAS and not self.project_id and not self.id:
            # Some legacy on platform formulas don't have a project_id so check if its already on platform
            raise ValueError("A project_id must be supplied for all formulas.")
        return self


class InventorySpecValue(BaseAlbertModel):
    """The acceptance value(s) of an [`InventorySpec`][albert.resources.inventory.InventorySpec].

    Expresses the expected value of a declared property as a range (``min`` to ``max``),
    a single ``reference`` value, and/or a ``comparison_operator``. Numeric inputs are
    accepted and stored as strings.

    Attributes
    ----------
    min : str | None
        The lower bound of the acceptable range.
    max : str | None
        The upper bound of the acceptable range.
    reference : str | None
        A reference or target value for the property.
    comparison_operator : str | None
        The operator used to compare a measured value against this spec
        (e.g. ``">"``, ``"<="``). Serialized as ``comparisonOperator``.
    """

    min: str | None = Field(default=None)
    max: str | None = Field(default=None)
    reference: str | None = Field(default=None)
    comparison_operator: str | None = Field(default=None, alias="comparisonOperator")

    @field_validator("min", "max", "reference", mode="before")
    @classmethod
    def cast_float_to_str(cls, v: Any) -> Any:
        if isinstance(v, int | float):
            return str(v)
        return v


class InventorySpec(BaseAlbertModel):
    """A declared property of an [`InventoryItem`][albert.resources.inventory.InventoryItem].

    A spec is a property asserted directly on an item (a declared expectation), as
    opposed to a value measured through a Task. Each spec points at a data column
    (``data_column_id``, format ``DAC...``) and carries the expected
    [`InventorySpecValue`][albert.resources.inventory.InventorySpecValue]. Specs are attached to and retrieved from an item via
    [`add_specs`][albert.collections.inventory.InventoryCollection.add_specs] and
    [`get_specs`][albert.collections.inventory.InventoryCollection.get_specs], and are
    grouped for an item by [`InventorySpecList`][albert.resources.inventory.InventorySpecList].

    !!! example
        ```python
        from albert.resources.inventory import InventorySpec, InventorySpecValue

        spec = InventorySpec(
            name="Viscosity",
            data_column_id="DAC1",
            value=InventorySpecValue(min=100, max=200),
        )
        ```

    Attributes
    ----------
    id : str | None
        The Albert ID of the spec. Serialized as ``albertId``.
    name : str
        The name of the spec. Required.
    data_column_id : str
        The ID of the data column this spec applies to (format ``DAC...``). Required.
        Serialized as ``datacolumnId``.
    data_column_name : str | None
        The display name of the data column. Serialized as ``datacolumnName``.
    data_template_id : str | None
        The ID of the associated data template. Serialized as ``datatemplateId``.
    data_template_name : str | None
        The display name of the data template. Serialized as ``datatemplateName``.
    unit_id : str | None
        The ID of the unit for the spec value. Serialized as ``unitId``.
    unit_name : str | None
        The display name of the unit. Serialized as ``unitName``.
    workflow_id : str | None
        The ID of the associated workflow. Serialized as ``workflowId``.
    workflow_name : str | None
        The display name of the workflow. Serialized as ``workflowName``.
    spec_config : str | None
        Additional spec configuration. Serialized as ``specConfig``.
    value : InventorySpecValue | None
        The expected value or range for the property. Serialized as ``Value``.

    See Also
    --------
    InventorySpecValue : The value/range carried by a spec.
    InventorySpecList : Groups the specs attached to a single item.
    """

    id: str | None = Field(default=None, alias="albertId")
    name: str
    data_column_id: str = Field(..., alias="datacolumnId")
    data_column_name: str | None = Field(default=None, alias="datacolumnName")
    data_template_id: str | None = Field(default=None, alias="datatemplateId")
    data_template_name: str | None = Field(default=None, alias="datatemplateName")
    unit_id: str | None = Field(default=None, alias="unitId")
    unit_name: str | None = Field(default=None, alias="unitName")
    workflow_id: str | None = Field(default=None, alias="workflowId")
    workflow_name: str | None = Field(default=None, alias="workflowName")
    spec_config: str | None = Field(default=None, alias="specConfig")
    value: InventorySpecValue | None = Field(default=None, alias="Value")


class InventorySpecList(BaseAlbertModel):
    """The set of [`InventorySpec`][albert.resources.inventory.InventorySpec] entries attached to one [`InventoryItem`][albert.resources.inventory.InventoryItem].

    Returned by
    [`get_specs`][albert.collections.inventory.InventoryCollection.get_specs] and accepted by
    [`add_specs`][albert.collections.inventory.InventoryCollection.add_specs], this binds a
    list of specs to the item they belong to.

    Attributes
    ----------
    parent_id : str
        The Inventory ID of the item the specs belong to. Serialized as ``parentId``.
    specs : list[InventorySpec]
        The specs attached to the item. Serialized as ``Specs``.

    See Also
    --------
    InventorySpec : An individual declared property in the list.
    """

    parent_id: str = Field(..., alias="parentId")
    specs: list[InventorySpec] = Field(..., alias="Specs")


# TODO: Find other pictogram items across the platform
# and see if this is unique to the search endpoint or a
# common resource
class InventorySearchPictogramItem(BaseAlbertModel):
    """A hazard pictogram entry returned on an [`InventorySearchItem`][albert.resources.inventory.InventorySearchItem]."""

    id: str
    name: str
    status: str | None = Field(default=None)


# This class is very similar to the UnNumber class,
# but the fields are not all required (and there is no Id in this one)
# if UnNumber doesn't require all fields we can
# merge these two classes together
class InventorySearchSDSItem(BaseAlbertModel):
    """Safety Data Sheet summary fields returned on an [`InventorySearchItem`][albert.resources.inventory.InventorySearchItem]."""

    un_number: str | None = Field(default=None, alias="unNumber")
    storage_class_name: str | None = Field(default=None, alias="storageClassName")
    shipping_description: str | None = Field(default=None, alias="shippingDescription")
    storage_class_number: str | None = Field(default=None, alias="storageClassNumber")
    un_classification: str | None = Field(default=None, alias="unClassification")


class InventorySearchItem(BaseAlbertModel, HydrationMixin[InventoryItem]):
    """A lightweight [`InventoryItem`][albert.resources.inventory.InventoryItem] result returned by the search endpoint.

    Search returns these partial records for speed; they carry the fields most useful
    for lookups, counts, and display rather than the full item. Produced by
    [`search`][albert.collections.inventory.InventoryCollection.search]. Because it mixes
    in [`HydrationMixin`][albert.resources._mixins.HydrationMixin], calling ``hydrate()`` on a
    bound instance fetches the corresponding fully populated [`InventoryItem`][albert.resources.inventory.InventoryItem].

    Attributes
    ----------
    id : str
        The Albert Inventory ID (format ``INV...``). Serialized as ``albertId``.
    name : str
        The name of the item.
    description : str
        The description of the item.
    category : InventoryCategory
        The kind of material this item represents.
    unit : InventoryUnitCategory
        The dimension the item is measured in.
    lots : list[dict[str, Any]]
        Lot records associated with the item.
    tags : list[Tag]
        Tags on the item.
    pictogram : list[InventorySearchPictogramItem]
        Hazard pictograms associated with the item.
    inventory_on_hand : float
        Total amount currently on hand. Defaults to 0 when absent (none on hand).
        Serialized as ``inventoryOnHand``.
    sds : InventorySearchSDSItem | None
        Safety Data Sheet summary fields. Serialized as ``SDS``.

    See Also
    --------
    InventoryItem : The fully populated item returned by ``hydrate()``.
    albert.collections.inventory.InventoryCollection.search : Produces these results.
    """

    id: str = Field(alias="albertId")
    name: str = Field(default="")
    description: str = Field(default="")
    category: InventoryCategory
    unit: InventoryUnitCategory
    lots: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[Tag] = Field(default_factory=list)
    pictogram: list[InventorySearchPictogramItem] = Field(default_factory=list)
    # missing element implies none on hand
    inventory_on_hand: float = Field(default=0.0, alias="inventoryOnHand")
    sds: InventorySearchSDSItem | None = Field(default=None, alias="SDS")


class MergeInventory(BaseAlbertModel):
    """The request payload for merging duplicate inventory items into one.

    Describes a merge: one surviving parent item plus the child item(s) to fold into
    it, and optionally which data modules to carry over. This is the body used by
    [`merge`][albert.collections.inventory.InventoryCollection.merge]; when ``modules``
    is omitted, all [`InventoryMergeModule`][albert.resources.inventory.InventoryMergeModule] values are included.

    !!! example
        ```python
        from albert.resources.inventory import MergeInventory

        merge = MergeInventory(
            parent_id="INVA1",
            child_inventories=[{"id": "INVB1"}, {"id": "INVC1"}],
        )
        ```

    Attributes
    ----------
    parent_id : InventoryId
        The Inventory ID of the item that will survive the merge. Serialized as
        ``parentId``.
    child_inventories : list[dict[str, InventoryId]]
        The child item(s) to merge into the parent, each given as a mapping such as
        ``{"id": "INVB1"}``. Serialized as ``ChildInventories``.
    modules : list[InventoryMergeModule] | None
        The data modules to carry over from the children. When ``None``, all modules
        are merged.

    See Also
    --------
    InventoryMergeModule : The set of mergeable data categories.
    albert.collections.inventory.InventoryCollection.merge : Consumes this payload.
    """

    parent_id: InventoryId = Field(alias="parentId")
    child_inventories: list[dict[str, InventoryId]] = Field(alias="ChildInventories")
    modules: list[InventoryMergeModule] | None = Field(default=None)
