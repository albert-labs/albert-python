from inspect import Parameter, Signature
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints

from pydantic import BaseModel, ConfigDict


def simplify_annotation(annotation: Any) -> str:
    """Simplifies complex type annotations into a readable form using `|` for unions."""
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in {Union, type(Any | None)}:  # Handle Union and UnionType
        non_none_args = [simplify_annotation(arg) for arg in args if arg is not type(None)]
        result = " | ".join(non_none_args)
        if type(None) in args:
            return f"{result} | None"
        return result

    if origin is Annotated:
        return simplify_annotation(args[0])

    if origin is not None:
        arg_str = ", ".join(simplify_annotation(arg) for arg in args)
        return f"{origin.__name__}[{arg_str}]"

    if hasattr(annotation, "__name__"):
        return annotation.__name__
    elif hasattr(annotation, "__origin__"):
        return annotation.__origin__.__name__

    return str(annotation)


# Custom metaclass to override signatures
class SignatureOverrideMeta(type(BaseModel)):
    def __new__(cls, name, bases, namespace, **kwargs):
        model_class = super().__new__(cls, name, bases, namespace, **kwargs)
        # Automatically generate the signature for all subclasses
        cls.generate_signature(model_class)
        return model_class

    @staticmethod
    def generate_signature(model):
        """Generate a signature with field names instead of aliases."""
        parameters = [
            Parameter(
                field_name,
                Parameter.KEYWORD_ONLY,
                default=field.default if field.default is not None else Parameter.empty,
                annotation=simplify_annotation(
                    get_type_hints(model).get(field_name, field.annotation)
                ),
            )
            for field_name, field in model.model_fields.items()
        ]
        model.__signature__ = Signature(parameters)


class BaseAlbertModel(BaseModel, metaclass=SignatureOverrideMeta):
    """Base class for Albert Pydantic models with default configuration settings."""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        cli_use_class_docs_for_groups=True,
        cli_ignore_unknown_args=True,
        use_attribute_docstrings=True,
    )
