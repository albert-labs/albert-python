from pydantic import BaseModel, ConfigDict


class BaseAlbertModel(BaseModel):
    """Base class for Albert Pydantic models with default configuration settings."""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        cli_use_class_docs_for_groups=True,
        cli_ignore_unknown_args=True,
        use_attribute_docstrings=True,
    )
