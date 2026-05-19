from __future__ import annotations

import re

import pandas as pd

DEPARTMENT_ALIASES = {
    "BOGOTA": "BOGOTA D.C.",
    "BOGOTA, D.C.": "BOGOTA D.C.",
    "BOGOTÁ D.C.": "BOGOTA D.C.",
    "D.C. BOGOTA": "BOGOTA D.C.",
    "SAN ANDRES Y PROVIDENCIA": "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA",
    "ARCHIPIELAGO DE SAN ANDRES Y PROVIDENCIA": "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA",
    "ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA": "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA",
    "GUAJIRA": "LA GUAJIRA",
}


def _strip_accents(value: str) -> str:
    replacements = str.maketrans(
        "ÁÉÍÓÚÜáéíóúüÑñ",
        "AEIOUUaeiouuNn",
    )
    return value.translate(replacements)



def normalize_department_name(value: object) -> str | pd.NA:
    if pd.isna(value):
        return pd.NA
    normalized = _strip_accents(str(value).strip().upper())
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.replace("  ", " ")
    normalized = DEPARTMENT_ALIASES.get(normalized, normalized)
    return normalized



def normalize_department_series(series: pd.Series) -> pd.Series:
    return series.apply(normalize_department_name).astype("string")
