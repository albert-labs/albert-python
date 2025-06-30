from pydantic import Field

from albert.core.shared.models.base import BaseResource


class UnNumber(BaseResource):
    """A UN number entity. UN Numbers are highly controlled within Albert.

    Attributes
    ----------
    un_number : str
        The UN number.
    id : str
        The Albert ID of the UN number. Set when the UN number is retrieved from Albert.
    storage_class_name : str
        The name of the storage class.
    shipping_description : str
        The shipping description.
    storage_class_number : str
        The storage class number.
    un_classification : str
        The UN classification.
    """

    un_number: str = Field(alias="unNumber")
    id: str = Field(alias="albertId")
    storage_class_name: str = Field(alias="storageClassName")
    shipping_description: str = Field(alias="shippingDescription")
    storage_class_number: str = Field(alias="storageClassNumber")
    un_classification: str = Field(alias="unClassification")
