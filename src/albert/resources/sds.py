from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import ConfigDict, Field, field_serializer

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import InventoryId, remove_id_prefix
from albert.resources.product_design import UnpackedProductDesign


class SDSDataEntity(str, Enum):
    """Entity names for [`get_field_options`][albert.collections.sds.SDSCollection.get_field_options].

    These are the ``entity`` query values accepted by the field-options endpoint.
    They do not always match the [`SDSRequest`][albert.resources.sds.SDSRequest] field name.

    Attributes
    ----------
    FLASHPOINT : str
        Options for ``flash_point``.
    BOILINGPOINT : str
        Options for ``initial_boiling_point``.
    ENFORCECLOAKING : str
        Options for ``enforce_cloaking``.
    VOC_UNIT : str
        Options for ``voc_content_unit``.
    """

    FLASHPOINT = "flashpoint"
    BOILINGPOINT = "boilingpoint"
    ENFORCECLOAKING = "enforcecloaking"
    VOC_UNIT = "vocUnit"
    MELTING_POINT_RANGE = "meltingPointRange"
    BOILING_POINT_RANGE = "boilingPointRange"
    VAPOR_PRESSURE = "vaporPressure"
    VAPOR_DENSITY = "vaporDensity"
    WATER_SOLUBILITY = "waterSolubility"
    AUTO_IGNITION_TEMP = "autoIgnitionTemp"
    DECOMPOSITION_TEMP = "decompositionTemp"
    PLM_NUMBER = "plmNumber"
    SECTION_15_DISCLOSURE = "section15Disclosure"
    UFI_IDENTIFIER = "ufiIdentifier"
    VISCOSITY_INPUT = "viscosityInput"
    PH_INPUT = "pHInput"
    PHYSICAL_STATE = "physicalState"
    FLAMMABILITY = "flammability"
    CURRENT_LOCATION = "currentLocation"
    DEFAULT_LOCATION = "defaultLocation"
    RECENT_CURRENT_LOCATION = "recentCurrentLocation"
    INTENDED_USE = "intendedUse"
    WASTE_CODE = "wasteCode"
    BURNING_TEST_RESULT = "burningTestResult"
    PARTICLE_CHARACTERISTICS = "particleCharacteristics"
    VISCOSITY = "viscosity"
    SPECIFIC_GRAVITY = "specificGravity"
    VISCOSITY_UNIT = "viscosityUnit"
    QUANTITY = "quantity_"
    INHALATION_CONTROL = "inhalationControl"
    CONTACT_CONTROL = "contactControl"
    MATERIAL_PHYSICAL_STATE = "materialPhysicalState"
    USE = "use"
    PHYSICAL_FORM = "physicalForm"
    GENERAL_INFO = "generalInfo"


class SDSLegalEntity(BaseAlbertModel):
    """A legal-entity option for a jurisdiction.

    Returned by
    [`get_legal_entities`][albert.collections.sds.SDSCollection.get_legal_entities].
    Send ``value`` as [`SDSRequest.legal_entity`][albert.resources.sds.SDSRequest.legal_entity].
    """

    legal_entity_id: int | None = Field(default=None, alias="legalEntityId")
    """The legal-entity identifier."""

    legal_entity_name: str | None = Field(default=None, alias="legalEntityName")
    """The display name of the legal entity."""

    value: int | None = Field(default=None)
    """The integer sent as ``legal_entity`` on [`SDSRequest`][albert.resources.sds.SDSRequest]."""

    is_default: bool | None = Field(default=None, alias="isDefault")
    """Whether this legal entity is the default for the jurisdiction."""


class SDSFieldOptions(BaseAlbertModel):
    """Tenant-specific options for one SDS input field.

    Returned by
    [`get_field_options`][albert.collections.sds.SDSCollection.get_field_options].
    When ``display`` is false, omit the field on
    [`SDSRequest`][albert.resources.sds.SDSRequest]. When ``data`` is a list of
    objects with a ``value`` key, send that ``value``.
    """

    display: bool | None = Field(default=None)
    """Whether the field should be shown and sent for this tenant."""

    is_required: bool | None = Field(default=None, alias="isRequired")
    """Whether the field is required for this tenant."""

    data: Any = Field(default=None)
    """The allowed values. Shape varies by entity (list of objects, list of strings, or empty)."""


class SDSRequest(BaseAlbertModel):
    """Input for generating an SDS for a formula inventory item.

    Identity fields (Albert ID, region, language, product type, physical state,
    legal entity) are required. Resolve codes from the SDS lookup helpers and
    send map **values** (e.g. ``"EN"``, ``"liquid"``), not display names.

    Product name and formula composition are not caller-supplied.
    [`generate_sds`][albert.collections.sds.SDSCollection.generate_sds] always
    loads the inventory name and unpacks the formula for CAS, ingredients, and
    inventory SDS rows.

    Formula inventory only (``INVMO…`` / ``MO…`` / ``INVP…``).
    """

    model_config = ConfigDict(extra="forbid")

    albert_id: InventoryId = Field(alias="albertID")
    """Formula inventory Albert ID. A leading ``INV`` is added if omitted and stripped when the request is sent."""

    product_type: str = Field(alias="productType")
    """Product-type code from [`get_products`][albert.collections.sds.SDSCollection.get_products] (e.g. ``"acrylate"``)."""

    language: str
    """Language code from [`get_languages`][albert.collections.sds.SDSCollection.get_languages] (e.g. ``"EN"``)."""

    region: str
    """Jurisdiction code from [`get_jurisdictions`][albert.collections.sds.SDSCollection.get_jurisdictions] (e.g. ``"US"``). Required; no default."""

    legal_entity: int = Field(alias="legalEntity")
    """Integer ``value`` from [`get_legal_entities`][albert.collections.sds.SDSCollection.get_legal_entities]."""

    physical_state: str = Field(alias="physicalState")
    """Physical-state code from [`get_physical_states`][albert.collections.sds.SDSCollection.get_physical_states] (e.g. ``"liquid"``)."""

    flash_point: float | None = Field(default=None, alias="flashPoint")
    """Flash-point option **value** from [`get_field_options`][albert.collections.sds.SDSCollection.get_field_options], not the display label."""

    initial_boiling_point: float | None = Field(default=None, alias="initialBoilingPoint")
    """Initial boiling point option value, optional."""

    viscosity: float | None = Field(default=None)
    """Dynamic viscosity, optional."""

    viscosity_unit: str | None = Field(default=None, alias="viscosityUnit")
    """Viscosity unit code (e.g. ``"cP"``), optional."""

    specific_gravity: float | None = Field(default=None, alias="specificGravity")
    """Specific gravity, optional."""

    color: str | None = Field(default=None)
    """Color description, optional."""

    odor: str | None = Field(default=None)
    """Odor description, optional."""

    voc_content: str | None = Field(default=None, alias="vocContent")
    """VOC content, optional."""

    voc_content_unit: str | None = Field(default=None, alias="vocContentUnit")
    """VOC unit from [`get_field_options`][albert.collections.sds.SDSCollection.get_field_options] with ``vocUnit``, optional."""

    ph_value: str | None = Field(default=None, alias="pHvalue")
    """pH range enum string (e.g. ``"2 ≤ pH ≤ 11.5"``), optional."""

    heat_of_reaction: str | None = Field(default=None, alias="heatOfReaction")
    """Heat-of-reaction enum string (e.g. ``"<300J/g"``), optional."""

    peroxide_check: str | None = Field(default=None, alias="peroxideCheck")
    """Peroxide check value, optional."""

    enforce_cloaking: bool | None = Field(default=None, alias="enforceCloaking")
    """When True, cloak CAS numbers on the SDS. Tenant-gated via field options."""

    section_15_disclosure: str | None = Field(default=None, alias="section15Disclosure")
    """Section 15 disclosure option value, optional."""

    project_color_formula_id: str | int | None = Field(default=None, alias="projectColorFormulaId")
    """Project / color / formula identifier, optional."""

    current_location: str | None = Field(default=None, alias="currentLocation")
    """Current location code, optional."""

    location: str | None = Field(default=None)
    """Location code, optional."""

    kinematic_viscosity_40: float | None = Field(default=None, alias="kinematicViscosity40")
    """Kinematic viscosity at 40°C in mm²/s, optional."""

    @field_serializer("albert_id")
    def _serialize_albert_id(self, value: str) -> str:
        return remove_id_prefix(value, "InventoryId")


class GeneratedSDS(BaseAlbertModel):
    """The SDS generated for a formula inventory item."""

    model_config = ConfigDict(extra="allow")

    id: str | None = Field(default=None)
    """The formula Albert ID associated with the generated SDS."""

    sds_json: dict[str, Any] = Field(alias="sds")
    """The generated SDS JSON (GHS sections plus extra keys such as coversheet and explainability)."""

    pdf_url: str | None = Field(default=None, alias="presignedURL")
    """Short-lived URL for the generated SDS PDF."""

    metadata_url: str | None = Field(default=None, alias="presignedURL_Metadata")
    """Short-lived URL for the generated SDS metadata spreadsheet, when present."""


def _dump_unpack_rows(rows: list[Any] | None) -> list[dict[str, Any]]:
    return [row.model_dump(by_alias=True, mode="json", exclude_none=True) for row in rows or []]


def _composition_from_unpacked(unpacked: UnpackedProductDesign) -> dict[str, Any]:
    return {
        "substances": _dump_unpack_rows(unpacked.substances),
        "cas_level_substances": _dump_unpack_rows(unpacked.cas_level_substances),
        "inventory_sds_list": _dump_unpack_rows(unpacked.inventory_sds_list),
    }
