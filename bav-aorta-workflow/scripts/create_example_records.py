"""Create example echocardiography records for testing the workflow.

The generated file is intended only to exercise the code path and column schema.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
rows = []

for patient_idx in range(1, 31):
    n_visits = 2 if patient_idx <= 20 else 3
    base_year = 2018 + (patient_idx % 5)
    age0 = rng.integers(35, 72)
    sex = "male" if rng.random() < 0.72 else "female"
    height = rng.normal(168 if sex == "male" else 160, 6)
    weight = rng.normal(72 if sex == "male" else 60, 8)
    sinus0 = rng.normal(34, 4)
    asc0 = rng.normal(39, 5)
    vmc2 = rng.choice(["rl_fusion", "rn_fusion", "ln_fusion", "unknown"], p=[0.65, 0.18, 0.05, 0.12])
    vmc1 = rng.choice(["three_sinus", "two_sinus"], p=[0.70, 0.30])

    for visit_idx in range(n_visits):
        if patient_idx <= 24:
            exam_date = pd.Timestamp(base_year, 1, 1) + pd.DateOffset(days=int(365.25 * visit_idx * rng.uniform(0.8, 2.2)))
        else:
            # Include several target visits inside a deployment-style date window.
            exam_date = pd.Timestamp("2023-06-01") if visit_idx == 0 else pd.Timestamp("2026-02-15")
        years = max((exam_date - pd.Timestamp(base_year, 1, 1)).days / 365.25, 0)
        sinus = sinus0 + 0.35 * years + rng.normal(0, 0.8)
        asc = asc0 + 0.45 * years + rng.normal(0, 0.9)
        rows.append(
            {
                "patient_id": f"P{patient_idx:03d}",
                "exam_date": exam_date.date().isoformat(),
                "bav_positive": 1,
                "age_years": int(age0 + years),
                "sex": sex,
                "height_cm": round(height, 1),
                "weight_kg": round(weight, 1),
                "systolic_bp": int(rng.normal(125, 12)),
                "diastolic_bp": int(rng.normal(75, 8)),
                "aortic_sinus_mm": round(sinus, 1),
                "ascending_aorta_mm": round(asc, 1),
                "aortic_stenosis_grade": rng.choice(["none", "mild", "moderate", "severe"], p=[0.35, 0.35, 0.20, 0.10]),
                "aortic_regurgitation_grade": rng.choice(["none", "mild", "moderate", "severe"], p=[0.30, 0.45, 0.20, 0.05]),
                "vmc1": vmc1,
                "vmc2": vmc2,
                "lv_edd_mm": round(rng.normal(50, 5), 1),
                "rv_ap_mm": round(rng.normal(24, 4), 1),
                "pulmonary_artery_mm": round(rng.normal(24, 3), 1),
                "av_vmax_m_s": round(rng.normal(2.2, 0.7), 2),
                "e_wave_cm_s": round(rng.normal(75, 15), 1),
                "ea_ratio": round(rng.normal(0.9, 0.25), 2),
            }
        )

out = Path("examples/example_echo_records.csv")
out.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(out, index=False)
print(f"Wrote {out}")
