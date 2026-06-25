"""Column schema utilities for the BAV aortic dimension workflow.

The workflow expects one row per echocardiographic examination. The schema keeps
site-specific report text outside the modelling code by requiring standardized field
names for routinely recorded measurements and morphology descriptors.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

# Fields that are required to construct current-to-future pairs and fit the residual model.
REQUIRED_COLUMNS = [
    "patient_id",
    "exam_date",
    "bav_positive",
    "age_years",
    "sex",
    "height_cm",
    "weight_kg",
    "systolic_bp",
    "diastolic_bp",
    "aortic_sinus_mm",
    "ascending_aorta_mm",
    "aortic_stenosis_grade",
    "aortic_regurgitation_grade",
    "vmc1",
    "vmc2",
]

# Optional structured echocardiographic fields. Sites can extend this list after local review.
OPTIONAL_COLUMNS = [
    "body_surface_area_m2",
    "lv_edd_mm",
    "rv_ap_mm",
    "pulmonary_artery_mm",
    "av_vmax_m_s",
    "e_wave_cm_s",
    "ea_ratio",
]

TARGET_COLUMNS = ["aortic_sinus_mm", "ascending_aorta_mm"]

CATEGORICAL_COLUMNS = [
    "sex",
    "aortic_stenosis_grade",
    "aortic_regurgitation_grade",
    "vmc1",
    "vmc2",
]

NUMERIC_COLUMNS = [
    "age_years",
    "height_cm",
    "weight_kg",
    "body_surface_area_m2",
    "systolic_bp",
    "diastolic_bp",
    "pulse_pressure",
    "aortic_sinus_mm",
    "ascending_aorta_mm",
    "lv_edd_mm",
    "rv_ap_mm",
    "pulmonary_artery_mm",
    "av_vmax_m_s",
    "e_wave_cm_s",
    "ea_ratio",
    "horizon_years",
]

DEFAULT_FEATURE_COLUMNS = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS


@dataclass(frozen=True)
class SchemaReport:
    """Result of checking a local table against the expected workflow schema."""

    missing_required: list[str]
    present_optional: list[str]
    absent_optional: list[str]

    @property
    def ok(self) -> bool:
        return len(self.missing_required) == 0


def check_schema(columns: Iterable[str]) -> SchemaReport:
    """Return required and optional schema coverage for a local input table."""
    observed = set(columns)
    missing_required = [c for c in REQUIRED_COLUMNS if c not in observed]
    present_optional = [c for c in OPTIONAL_COLUMNS if c in observed]
    absent_optional = [c for c in OPTIONAL_COLUMNS if c not in observed]
    return SchemaReport(missing_required, present_optional, absent_optional)
