from typing import Annotated, Any

import pandas as pd
from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema


def _deserialize_tight_dataframe(df: Any) -> pd.DataFrame:
    if isinstance(df, pd.DataFrame):
        return df
    result = pd.DataFrame.from_dict(df, orient="tight")
    # JSON null deserializes to None, but object-dtype columns should preserve NaN
    for col in result.select_dtypes(include="object").columns:
        result[col] = result[col].where(result[col].notna(), float("nan"))
    return result


OrientTightDataFrame = Annotated[
    pd.DataFrame,
    BeforeValidator(_deserialize_tight_dataframe),
    PlainSerializer(lambda df: df.to_dict(orient="tight"), return_type=dict),
    WithJsonSchema({"type": "object"}),
]
