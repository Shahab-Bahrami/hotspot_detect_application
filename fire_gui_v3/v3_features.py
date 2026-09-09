"""Online Version 3 feature computation matching the study workbook contract."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

EARTH_KM = 6371.0088
RADII = (("500m", 0.5), ("1km", 1.0), ("5km", 5.0), ("10km", 10.0))
WINDOWS = (("1h", 1), ("6h", 6), ("24h", 24), ("7d", 168), ("30d", 720), ("90d", 2160))
LABEL_RADII = (("500m", 0.5), ("1km", 1.0), ("10km", 10.0))
POSITIVE = {"Verified Fire", "Fire inside Sitrep"}


def _distances_km(history: pd.DataFrame, longitude: float, latitude: float) -> np.ndarray:
    lon1, lat1 = np.radians([longitude, latitude])
    lon2 = np.radians(history.Longitude.to_numpy(dtype=float))
    lat2 = np.radians(history.Latitude.to_numpy(dtype=float))
    dlon, dlat = lon2 - lon1, lat2 - lat1
    value = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return EARTH_KM * 2 * np.arctan2(np.sqrt(value), np.sqrt(np.maximum(0, 1 - value)))


class OnlineFeatureBuilder:
    def __init__(self, history: pd.DataFrame, normalization_path: Path):
        self.history = history.copy()
        self.history["Tgl_Hotspot"] = pd.to_datetime(self.history.Tgl_Hotspot)
        self.history["Status"] = self.history.Status.fillna("Unverified").astype(str)
        self.history["Satellite"] = self.history.Satellite.fillna("[missing]").astype(str)
        rows = json.loads(normalization_path.read_text(encoding="utf-8"))
        self.normalization = {row["feature"]: row for row in rows}

    def _normalize(self, feature: str, value: float | int | None) -> tuple[float, int]:
        rule = self.normalization[feature]
        missing = value is None or not np.isfinite(float(value))
        transformed = float(rule["missing_fill_transformed"]) if missing else float(value)
        if rule["transform"] == "log1p_robust" and not missing:
            transformed = math.log1p(max(transformed, 0.0))
        if rule["transform"] != "identity":
            transformed = min(max(transformed, float(rule["clip_low_transformed"])), float(rule["clip_high_transformed"]))
            transformed = (transformed - float(rule["center_transformed"])) / float(rule["scale_transformed"])
        return float(transformed), int(missing)

    def build(self, longitude: float, latitude: float, at: pd.Timestamp, source: str, satellite: str, region: str) -> pd.DataFrame:
        at = pd.Timestamp(at)
        # Strictly earlier excludes the candidate and its complete timestamp batch.
        prior = self.history[self.history.Tgl_Hotspot < at].copy()
        distances = _distances_km(prior, longitude, latitude)
        delta_h = (at - prior.Tgl_Hotspot).dt.total_seconds().to_numpy() / 3600
        sat_values = prior.Satellite.to_numpy(dtype=object)
        statuses = prior.Status.to_numpy(dtype=object)

        raw: dict[str, float | int | None] = {
            "Longitude": longitude,
            "Latitude": latitude,
            "month": at.month,
            "day_of_year": at.dayofyear,
            "hour_local_recorded": at.hour + at.minute / 60,
            "day_of_week": at.dayofweek,
            "quarter": at.quarter,
            "is_weekend": int(at.dayofweek >= 5),
            "is_nominal_dry_season_may_oct": int(5 <= at.month <= 10),
            "doy_sin": math.sin(2 * math.pi * (at.dayofyear - 1) / 365.25),
            "doy_cos": math.cos(2 * math.pi * (at.dayofyear - 1) / 365.25),
            "month_sin": math.sin(2 * math.pi * (at.month - 1) / 12),
            "month_cos": math.cos(2 * math.pi * (at.month - 1) / 12),
            "hour_sin": math.sin(2 * math.pi * (at.hour + at.minute / 60) / 24),
            "hour_cos": math.cos(2 * math.pi * (at.hour + at.minute / 60) / 24),
            "dow_sin": math.sin(2 * math.pi * at.dayofweek / 7),
            "dow_cos": math.cos(2 * math.pi * at.dayofweek / 7),
        }

        for radius_name, radius in RADII:
            within = distances <= radius + 1e-10
            for window_name, hours in WINDOWS:
                raw[f"count_r{radius_name}_w{window_name}_prior"] = int((within & (delta_h <= hours)).sum())

        for radius_name, radius in LABEL_RADII:
            within = distances <= radius + 1e-10
            ids = np.flatnonzero(within)
            if len(ids):
                latest_delta = float(delta_h[ids].min())
                latest_ids = ids[np.isclose(delta_h[ids], latest_delta, rtol=0, atol=1e-10)]
                latest_closest = latest_ids[np.argmin(distances[latest_ids])]
                raw[f"time_since_prev_alert_r{radius_name}_hours"] = latest_delta
                raw[f"distance_to_prev_alert_r{radius_name}_km"] = float(distances[latest_closest])
            else:
                raw[f"time_since_prev_alert_r{radius_name}_hours"] = None
                raw[f"distance_to_prev_alert_r{radius_name}_km"] = None
            other = within & (sat_values != satellite)
            raw[f"time_since_prev_other_sat_r{radius_name}_hours"] = float(delta_h[other].min()) if other.any() else None

            determinate = np.isin(statuses, ["Verified Fire", "Fire inside Sitrep", "Verified No fire"])
            fire = np.isin(statuses, list(POSITIVE))
            prior_fire = within & determinate & fire
            raw[f"time_since_prior_fire_r{radius_name}_hours"] = float(delta_h[prior_fire].min()) if prior_fire.any() else None
            for window_name, hours in (("30d", 720), ("90d", 2160), ("all", np.inf)):
                mask = within & determinate & (delta_h <= hours)
                count = int(mask.sum())
                fire_count = int((mask & fire).sum())
                stem = f"r{radius_name}_w{window_name}"
                raw[f"prior_determinate_count_{stem}"] = count
                raw[f"prior_fire_count_{stem}"] = fire_count
                raw[f"prior_no_fire_count_{stem}"] = count - fire_count
                raw[f"prior_fire_rate_smoothed_{stem}"] = (fire_count + 1) / (count + 2)

        within_10 = distances <= 10 + 1e-10
        for window_name, hours in (("24h", 24), ("30d", 720)):
            mask = within_10 & (delta_h <= hours)
            raw[f"nearest_prior_distance_r10km_w{window_name}_km"] = float(distances[mask].min()) if mask.any() else None

        row: dict[str, object] = {
            "Sumber": str(source or "[missing]"),
            "Satellite": str(satellite or "[missing]"),
            "Region": str(region or "[missing]"),
        }
        for feature, value in raw.items():
            normalized, missing = self._normalize(feature, value)
            row[f"{feature}__norm"] = normalized
            if missing or f"{feature}__missing" in {
                "time_since_prev_alert_r500m_hours__missing", "distance_to_prev_alert_r500m_km__missing",
                "time_since_prev_other_sat_r500m_hours__missing", "time_since_prev_alert_r1km_hours__missing",
                "distance_to_prev_alert_r1km_km__missing", "time_since_prev_other_sat_r1km_hours__missing",
                "time_since_prev_alert_r10km_hours__missing", "distance_to_prev_alert_r10km_km__missing",
                "time_since_prev_other_sat_r10km_hours__missing", "nearest_prior_distance_r10km_w24h_km__missing",
                "nearest_prior_distance_r10km_w30d_km__missing", "time_since_prior_fire_r500m_hours__missing",
                "time_since_prior_fire_r1km_hours__missing", "time_since_prior_fire_r10km_hours__missing",
            }:
                row[f"{feature}__missing"] = missing
        return pd.DataFrame([row])
