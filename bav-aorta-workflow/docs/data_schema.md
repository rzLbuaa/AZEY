# Data schema

The input table should contain one row per echocardiographic examination. Date columns should use ISO format (`YYYY-MM-DD`) when possible.

## Required columns

| Column | Description |
|---|---|
| `patient_id` | Local patient identifier used to order serial examinations. |
| `exam_date` | Echocardiography examination date. |
| `bav_positive` | BAV status, encoded as 1 for BAV-positive and 0 otherwise. |
| `age_years` | Age at examination. |
| `sex` | Sex label, for example `male` or `female`. |
| `height_cm` | Height in centimeters. |
| `weight_kg` | Weight in kilograms. |
| `systolic_bp` | Systolic blood pressure in mmHg. |
| `diastolic_bp` | Diastolic blood pressure in mmHg. |
| `aortic_sinus_mm` | Aortic sinus diameter in millimeters. |
| `ascending_aorta_mm` | Ascending aorta diameter in millimeters. |
| `aortic_stenosis_grade` | Aortic stenosis grade: `none`, `mild`, `moderate`, `severe`, or local equivalents. |
| `aortic_regurgitation_grade` | Aortic regurgitation grade: `none`, `mild`, `moderate`, `severe`, or local equivalents. |
| `vmc1` | Sinus-level morphology label, for example `three_sinus` or `two_sinus`. |
| `vmc2` | Valve morphology label, for example `rl_fusion`, `rn_fusion`, `ln_fusion`, `trileaflet`, or `unknown`. |

## Optional columns

| Column | Description |
|---|---|
| `body_surface_area_m2` | Body surface area. If absent, a Mosteller estimate is calculated from height and weight. |
| `lv_edd_mm` | Left ventricular end-diastolic diameter. |
| `rv_ap_mm` | Right ventricular anteroposterior diameter. |
| `pulmonary_artery_mm` | Main pulmonary artery diameter. |
| `av_vmax_m_s` | Aortic valve peak velocity. |
| `e_wave_cm_s` | Mitral E-wave velocity. |
| `ea_ratio` | E/A ratio. |

## Pair construction rule

For each BAV-positive patient, examinations are sorted by date. Consecutive examinations are paired when the follow-up interval is at least 0.5 years and no more than 5 years. Predictors come only from the earlier examination; target diameters come from the later examination.
