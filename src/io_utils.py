"""Shared IO helpers."""
import pandas as pd

# The claim-class label "null" must survive as a string; pandas' default
# NA list would turn it into NaN. Empty cells and nan spellings from
# to_csv still parse as missing values.
_NA = ["", "nan", "NaN", "NAN", "None"]


def read_scores(path: str) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=False, na_values=_NA,
                       dtype={"pmid": str})
