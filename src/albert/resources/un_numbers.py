from pydantic import Field

from albert.core.shared.models.base import BaseResource


class UnNumber(BaseResource):
    """A United Nations hazardous-materials shipping identifier.

    A UN Number identifies a hazardous material for transport and carries the
    associated shipping description and storage-class metadata used when
    classifying substances and inventory items. UN Numbers are highly controlled
    within Albert and cannot be created through the SDK; retrieve them with
    [`UnNumberCollection`][albert.collections.un_numbers.UnNumberCollection].

    Attributes
    ----------
    un_number : str
        The UN Number itself (e.g. ``"UN1090"``).
    id : str
        The Albert ID of the UN Number. Set when the UN Number is retrieved from
        Albert.
    storage_class_name : str
        The name of the associated storage class.
    shipping_description : str
        The proper shipping description for the material.
    storage_class_number : str
        The number of the associated storage class.
    un_classification : str
        The UN hazard classification.
    """

    un_number: str = Field(alias="unNumber")
    id: str = Field(alias="albertId")
    storage_class_name: str = Field(alias="storageClassName")
    shipping_description: str = Field(alias="shippingDescription")
    storage_class_number: str = Field(alias="storageClassNumber")
    un_classification: str = Field(alias="unClassification")
