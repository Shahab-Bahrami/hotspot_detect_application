"""Small inference-time subset of fire_modeling used by the packaged GUI."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

NUMERIC = [
    "Longitude", "Latitude",
    "doy_sin", "doy_cos", "month_sin", "month_cos", "hour_sin", "hour_cos",
]
CATEGORICAL = ["Sumber", "Satellite", "Region"]
FEATURES = NUMERIC + CATEGORICAL
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


def load_data(workbook: Path) -> pd.DataFrame:
    """Load the determinate labeled history needed by the hybrid model."""
    frame = load_reports(workbook)
    frame = frame[frame["Status"] != "Unverified"].copy()
    return frame.reset_index(drop=True)


def make_history_maps(frame: pd.DataFrame, year: int, resolution: float = .05):
    """Build spatial-history channels from years strictly before the requested year."""
    past = frame[frame.Year < year]
    lon0, lat0 = 101.5, -4.3
    nx, ny = 96, 76
    alert = np.zeros((ny, nx), dtype="float32")
    fire = np.zeros((ny, nx), dtype="float32")
    ix = np.floor((past.Longitude.to_numpy() - lon0) / resolution).astype(int)
    iy = np.floor((past.Latitude.to_numpy() - lat0) / resolution).astype(int)
    valid = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    np.add.at(alert, (iy[valid], ix[valid]), 1)
    np.add.at(fire, (iy[valid], ix[valid]), past.target.to_numpy()[valid])
    rate = (fire + 1) / (alert + 2)
    density = np.log1p(alert)
    if density.max() > 0:
        density /= density.max()
    return np.stack([density, rate], axis=-1), (lon0, lat0, resolution)


def extract_patches(frame, maps_by_year, meta, radius: int = 4):
    """Extract the local spatial patch consumed by the hybrid CNN."""
    lon0, lat0, resolution = meta
    width = radius * 2 + 1
    patches = np.zeros((len(frame), width, width, 2), dtype="float32")
    for j, (_, row) in enumerate(frame.iterrows()):
        grid = maps_by_year[int(row.Year)]
        ix = int(np.floor((row.Longitude - lon0) / resolution))
        iy = int(np.floor((row.Latitude - lat0) / resolution))
        padded = np.pad(grid, ((radius, radius), (radius, radius), (0, 0)))
        ix = np.clip(ix, 0, grid.shape[1] - 1) + radius
        iy = np.clip(iy, 0, grid.shape[0] - 1) + radius
        patches[j] = padded[iy-radius:iy+radius+1, ix-radius:ix+radius+1]
    return patches
