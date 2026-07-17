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

    storage_class_name: str = Field(alias="storageClassName")
    """The name of the associated storage class."""

    shipping_description: str = Field(alias="shippingDescription")
    """The proper shipping description for the material."""

    storage_class_number: str = Field(alias="storageClassNumber")
    """The number of the associated storage class."""

    un_classification: str = Field(alias="unClassification")
    """The UN hazard classification."""
