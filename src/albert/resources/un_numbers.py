from pydantic import Field

from albert.core.shared.models.base import BaseResource


class UnNumber(BaseResource):
    """A United Nations hazardous-materials shipping identifier.

    A UN Number identifies a hazardous material for transport and carries the
    associated shipping description and storage-class metadata used when
    classifying substances and inventory items. UN Numbers are highly controlled
    within Albert and cannot be created through the SDK; retrieve them with
    [`UnNumberCollection`][albert.collections.un_numbers.UnNumberCollection]."""

    un_number: str = Field(alias="unNumber")
    """The UN Number itself (e.g. ``"UN1090"``)."""

    id: str = Field(alias="albertId")
    """The Albert ID of the UN Number. Set when the UN Number is retrieved from Albert."""

    storage_class_name: str | None = Field(default=None, alias="storageClassName")
    """The name of the associated storage class. Omitted on sparse records."""

    shipping_description: str | None = Field(default=None, alias="shippingDescription")
    """The proper shipping description for the material. Omitted on sparse records."""

    storage_class_number: str = Field(alias="storageClassNumber")
    """The number of the associated storage class."""

    un_classification: str | None = Field(default=None, alias="unClassification")
    """The UN hazard classification. Omitted on sparse records."""
