"""Spatial and temporal summaries for historical hotspot reports."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

FIRE_STATUSES = {"Verified Fire", "Fire inside Sitrep"}
DISTANCE_BANDS_KM = (0.5, 1.0, 2.0, 5.0, 10.0)


def _rate(fires: int, evaluated: int):
    return round(100 * fires / evaluated, 1) if evaluated else None


def _counts(frame: pd.DataFrame) -> dict:
    evaluated = int((frame.Status != "Unverified").sum())
    fires = int(frame.Status.isin(FIRE_STATUSES).sum())
    return {
        "reports": int(len(frame)),
        "evaluated": evaluated,
        "fires": fires,
        "no_fire": int((frame.Status == "Verified No fire").sum()),
        "unverified": int((frame.Status == "Unverified").sum()),
        "fire_rate": _rate(fires, evaluated),
    }


def _distances_km(frame: pd.DataFrame, longitude: float, latitude: float) -> np.ndarray:
    """Vectorized haversine distance from a point to all frame rows."""
    lon1 = np.radians(float(longitude))
    lat1 = np.radians(float(latitude))
    lon2 = np.radians(frame.Longitude.to_numpy(dtype=float))
    lat2 = np.radians(frame.Latitude.to_numpy(dtype=float))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    value = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * np.arctan2(np.sqrt(value), np.sqrt(np.maximum(0, 1 - value)))


def nearby_context(
    reports: pd.DataFrame,
    longitude: float,
    latitude: float,
    at: datetime,
    radius_km: float = 5.0,
    lookback_days: int | None = None,
    row_limit: int = 40,
) -> dict:
    """Return leakage-safe report context available on or before ``at``."""
    longitude = float(longitude)
    latitude = float(latitude)
    radius_km = float(radius_km)
    if not (np.isfinite(longitude) and np.isfinite(latitude) and -180 <= longitude <= 180 and -90 <= latitude <= 90):
        raise ValueError("Coordinates are outside valid longitude/latitude bounds.")
    if not np.isfinite(radius_km) or radius_km < 0.1 or radius_km > 50:
        raise ValueError("Radius must be between 0.1 and 50 km.")
    if lookback_days is not None and not 1 <= int(lookback_days) <= 36500:
        raise ValueError("Lookback must be between 1 and 36,500 days.")

    eligible = reports[reports.Tgl_Hotspot <= at].copy()
    if lookback_days is not None:
        eligible = eligible[eligible.Tgl_Hotspot >= at - timedelta(days=int(lookback_days))].copy()
    eligible["distance_km"] = _distances_km(eligible, longitude, latitude)
    selected = eligible[eligible.distance_km <= radius_km].copy()

    summary = _counts(selected)
    summary["nearest_km"] = round(float(selected.distance_km.min()), 3) if len(selected) else None
    summary["earliest"] = selected.Tgl_Hotspot.min().isoformat() if len(selected) else None
    summary["latest"] = selected.Tgl_Hotspot.max().isoformat() if len(selected) else None

    bands = []
    for band in DISTANCE_BANDS_KM:
        counts = _counts(eligible[eligible.distance_km <= band])
        bands.append({"radius_km": band, **counts})

    yearly = []
    for year, group in selected.groupby(selected.Tgl_Hotspot.dt.year, sort=True):
        yearly.append({"year": int(year), **_counts(group)})

    monthly = []
    month_groups = selected.groupby(selected.Tgl_Hotspot.dt.to_period("M"), sort=True)
    for month, group in month_groups:
        monthly.append({"month": str(month), **_counts(group)})

    statuses = [
        {"status": str(status), "reports": int(count)}
        for status, count in selected.Status.value_counts().items()
    ]
    ordered = selected.sort_values(["distance_km", "Tgl_Hotspot"], ascending=[True, False]).head(row_limit)
    rows = [
        {
            "date": row.Tgl_Hotspot.isoformat(),
            "distance_km": round(float(row.distance_km), 3),
            "longitude": round(float(row.Longitude), 6),
            "latitude": round(float(row.Latitude), 6),
            "status": str(row.Status),
            "source": str(row.Sumber),
            "satellite": str(row.Satellite),
            "region": str(row.Region),
        }
        for row in ordered.itertuples(index=False)
    ]
    return {
        "query": {
            "longitude": longitude,
            "latitude": latitude,
            "at": at.isoformat(),
            "radius_km": radius_km,
            "lookback_days": lookback_days,
            "future_rows_excluded": True,
        },
        "summary": summary,
        "distance_bands": bands,
        "yearly": yearly,
        "monthly": monthly,
        "statuses": statuses,
        "rows": rows,
        "rows_truncated": max(0, len(selected) - len(rows)),
    }


def dataset_profile(reports: pd.DataFrame) -> dict:
    """Compact workbook-wide context suitable for an LLM prompt."""
    def grouped_counts(column: str) -> dict:
        table = reports.groupby([column, "Status"]).size().unstack(fill_value=0)
        return {
            str(index): {str(status): int(count) for status, count in row.items()}
            for index, row in table.iterrows()
        }

    years = []
    for year, group in reports.groupby(reports.Tgl_Hotspot.dt.year, sort=True):
        years.append({"year": int(year), **_counts(group)})
    months = []
    for month, group in reports.groupby(reports.Tgl_Hotspot.dt.to_period("M"), sort=True):
        months.append({"month": str(month), **_counts(group)})
    return {
        "report_count": int(len(reports)),
        "date_start": reports.Tgl_Hotspot.min().isoformat(),
        "date_end": reports.Tgl_Hotspot.max().isoformat(),
        "columns": ["Longitude", "Latitude", "Tgl_Hotspot", "Sumber", "Satellite", "Status", "Region"],
        "status_totals": reports.Status.value_counts().astype(int).to_dict(),
        "region_totals": reports.Region.value_counts().astype(int).to_dict(),
        "source_totals": reports.Sumber.value_counts().astype(int).to_dict(),
        "satellite_totals": reports.Satellite.value_counts().astype(int).to_dict(),
        "yearly": years,
        "monthly": months,
        "status_by_region": grouped_counts("Region"),
        "status_by_source": grouped_counts("Sumber"),
        "status_by_satellite": grouped_counts("Satellite"),
        "fire_definition": sorted(FIRE_STATUSES),
        "fire_rate_denominator": "determinate reports only; Unverified is excluded",
    }
