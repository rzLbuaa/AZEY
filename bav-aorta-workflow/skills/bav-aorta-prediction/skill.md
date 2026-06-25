# BAV Aortic Prediction Workflow Skill

## Purpose

Use this workflow skill when a local structured echocardiography table needs to be converted into current-to-future BAV follow-up pairs, residual aortic dimension predictions, performance summaries, and reviewable workflow artifacts.

## Inputs

The input is a CSV table with one row per transthoracic echocardiographic examination. Required fields include patient identifier, examination date, BAV-positive indicator, age, sex, height, weight, blood pressure, current aortic sinus diameter, current ascending aorta diameter, aortic stenosis grade, aortic regurgitation grade, and BAV morphology descriptors.

Optional structured measurements may include body surface area, cardiac chamber dimensions, Doppler measurements, pulmonary artery diameter, and diastolic filling indices.

## Procedure

1. Check that required variables are present.
2. Normalize morphology labels and valve dysfunction grades.
3. Order BAV-positive examinations within each patient.
4. Construct current-to-future pairs using only the earlier examination as input.
5. Split training-period and deployment-period pairs by the future/reference examination date.
6. Fit residual models for aortic sinus and ascending aorta diameter change.
7. Reconstruct predicted future dimensions from current diameter plus predicted change.
8. Export metrics, predictions, pair files, feature-importance summaries, and an audit log.

## Outputs

The workflow writes pair files, training and validation predictions, target-level metrics, feature importance, a run summary, and an audit log. These outputs are intended for local review, figure generation, and report preparation.

## Interpretation

Predictions are future-dimension reference estimates for clinician review. They are not treatment decisions. Site-specific deployment should be reviewed with local clinicians, with attention to schema mapping, measurement practice, morphology labels, validation window, and local governance requirements.
