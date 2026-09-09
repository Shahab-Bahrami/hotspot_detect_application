"""Workbook loading used by the packaged Version 3 application."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CATEGORICAL = ["Sumber", "Satellite", "Region"]
POSITIVE = {"Verified Fire", "Fire inside Sitrep"}


def load_reports(workbook: Path) -> pd.DataFrame:
    """Load and normalize every report in the bundled workbook."""
    parts = []
    for sheet in ["2019", "2023", "2025", "2026"]:
        data = pd.read_excel(workbook, sheet_name=sheet, engine="openpyxl").dropna(how="all")
        data["Year"] = int(sheet)
        parts.append(data)
    frame = pd.concat(parts, ignore_index=True)
    frame["Tgl_Hotspot"] = pd.to_datetime(frame["Tgl_Hotspot"])
    frame["Status"] = frame["Status"].fillna("Unverified").astype(str)
    frame["target"] = frame["Status"].isin(POSITIVE).astype("int8")
    for column in CATEGORICAL:
        frame[column] = frame[column].fillna("[missing]").astype(str).replace("", "[missing]")
    return frame.reset_index(drop=True)
