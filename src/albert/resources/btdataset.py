from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import BTDatasetId, ProjectId
from albert.core.shared.models.base import BaseResource, EntityLink


class BTDatasetReferences(BaseAlbertModel):
    """The Albert entities a Breakthrough dataset was assembled from.

    Records which projects, data columns, targets, and worksheets contributed the
    data in a [`BTDataset`][albert.resources.btdataset.BTDataset], plus any filter applied when the data was pulled.

    Attributes
    ----------
    project_ids : list of str
        Identifiers of the projects the data was drawn from (format ``PRO...``).
    data_column_ids : list of str or None
        Identifiers of the data columns included (format ``DAC...``).
    target_ids : list of str or None
        Identifiers of the targets included (format ``TAR...``).
    sheet_ids : list of str or None
        Identifiers of the worksheets the data was drawn from (format ``WKS...``).
    filter : dict or None
        Free-form filter criteria applied when assembling the data.
    """

    project_ids: list[str]
    data_column_ids: list[str] | None = Field(default=None)
    target_ids: list[str] | None = Field(default=None)
    sheet_ids: list[str] | None = Field(default=None)
    filter: dict[str, Any] | None = Field(default=None)


class BTDataset(BaseResource):
    """A dataset used to build and train Breakthrough models.

    Albert Breakthrough is Albert's inverse-design / ML optimization capability. A dataset holds the tabular
    data that Breakthrough model sessions and models
    ([`BTModelSession`][albert.resources.btmodel.BTModelSession],
    [`BTModel`][albert.resources.btmodel.BTModel]) are trained on; their ``dataset_id``
    points back to a dataset. Datasets are managed through
    [`BTDatasetCollection`][albert.collections.btdataset.BTDatasetCollection].

    A ``BTDataset`` and a [`SmartDataset`][albert.resources.smart_datasets.SmartDataset] are
    distinct entities that share an ETL engine (Zeus stored procedures) but are not
    interchangeable: a ``BTDataset`` is a Breakthrough pointer record (its dataset
    rows are stored in S3), while a ``SmartDataset`` is a Smart Projects entity. A
    SmartDataset is not itself an input to Albert Breakthrough.

    !!! example
        ```python
        from albert.resources.btdataset import BTDataset

        dataset = BTDataset(name="Coatings training set")
        ```

    Attributes
    ----------
    name : str
        Human-readable name of the dataset.
    id : BTDatasetId or None
        Unique identifier of the dataset (format ``DST...``). Assigned by Albert on
        creation.
    parent_id : ProjectId or None
        Identifier of the project the dataset belongs to (format ``PRO...``).
    key : str or None
        Storage key for the dataset's underlying data file, if applicable.
    file_name : str or None
        Name of the dataset's underlying data file, if applicable.
    report : EntityLink or None
        Link to a related report, if any.
    references : BTDatasetReferences or None
        The Albert entities the dataset was assembled from.
    """

    name: str
    id: BTDatasetId | None = Field(default=None, alias="albertId")
    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    key: str | None = Field(default=None)
    file_name: str | None = Field(default=None, alias="fileName")
    report: EntityLink | None = Field(default=None, alias="Report")
    references: BTDatasetReferences | None = Field(default=None, alias="References")
