# BAV Aortic Dimension Workflow

This repository contains a structured echocardiography workflow for estimating future aortic sinus and ascending aorta dimensions in adults with bicuspid aortic valve (BAV). The workflow uses routine examination variables, constructs current-to-future follow-up pairs, fits residual models, evaluates deployment-period predictions, and generates figure-ready outputs.

## Clinical objective

During routine echocardiographic assessment of a BAV-positive patient, clinicians can measure the current aortic sinus and ascending aorta diameters, but a patient-specific estimate of future change is not usually available at the examination. The workflow uses information already recorded during standard transthoracic echocardiography to provide a clinician-reviewable future-dimension reference.

## Repository structure

```text
bav-aorta-workflow/
├── src/bav_aorta_workflow/
│   ├── schema.py              # expected column schema and schema checking
│   ├── pipeline.py            # pair construction, residual model, evaluation, exports
│   ├── agent.py               # deterministic workflow orchestration layer
│   ├── skill.py               # reusable skill interface for local integration
│   ├── figures.py             # Python figure generation from workflow outputs
│   ├── cli.py                 # workflow command-line interface
│   ├── agent_cli.py           # agent command-line interface
│   ├── figure_cli.py          # figure-generation command-line interface
│   └── __init__.py
├── skills/
│   └── bav-aorta-prediction/
│       └── skill.md
├── scripts/
│   ├── create_example_records.py
│   ├── run_example.py
│   ├── run_agent_example.py
│   └── plot_figures.py
├── docs/
│   ├── data_schema.md
│   └── workflow_agent.md
├── examples/
│   └── .gitkeep
├── figures/
│   └── README.md
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Workflow modules

The workflow has six core modules:

1. **Schema checking**: confirm that the local echocardiography table contains required demographic, measurement, valve-function, morphology, and date fields.
2. **Label harmonization**: normalize valve dysfunction grades and BAV morphology labels into a consistent vocabulary.
3. **Pair construction**: order BAV-positive examinations by patient and date; use the earlier examination as model input and the later examination as endpoint.
4. **Residual modelling**: train separate residual regressors for aortic sinus and ascending aorta diameter change.
5. **Deployment-period evaluation**: compare model outputs with reference measurements and report millimeter-scale error summaries.
6. **Figure generation**: generate Python figures from exported prediction and metric files.

## Workflow agent and skill

The package includes a deterministic workflow agent and a reusable skill interface.

The agent coordinates schema review, record preparation, pair construction, temporal split, residual model training, evaluation, export, and audit-log generation:

```bash
bav-aorta-agent \
  --input examples/example_echo_records.csv \
  --output-dir example_outputs_agent \
  --validation-start 2026-01-01 \
  --validation-end 2026-03-31
```

The same interface can be used from Python:

```python
from bav_aorta_workflow.agent import AortaWorkflowAgent, WorkflowAgentConfig

config = WorkflowAgentConfig(
    validation_start="2026-01-01",
    validation_end="2026-03-31",
)
result = AortaWorkflowAgent(config).run(
    input_csv="examples/example_echo_records.csv",
    output_dir="example_outputs_agent",
)
print(result.to_dict())
```

The skill interface exposes a compact input/output contract for integration into a local data workflow:

```python
from bav_aorta_workflow.skill import BAVAortaPredictionSkill

skill = BAVAortaPredictionSkill()
print(skill.describe())
summary = skill.run(
    input_csv="examples/example_echo_records.csv",
    output_dir="example_outputs_skill",
)
```

See `docs/workflow_agent.md` and `skills/bav-aorta-prediction/skill.md` for the orchestration and skill descriptions.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e .
```

## Run the example

Generate example records:

```bash
python scripts/create_example_records.py
```

Run the standard workflow:

```bash
bav-aorta-run \
  --input examples/example_echo_records.csv \
  --output-dir example_outputs \
  --validation-start 2026-01-01 \
  --validation-end 2026-03-31
```

Run through the agent interface:

```bash
python scripts/run_agent_example.py
```

## Output files

The workflow writes the following files to the selected output directory:

```text
all_constructed_pairs.csv
training_pairs.csv
prospective_validation_pairs.csv
training_predictions.csv
prospective_validation_predictions.csv
training_metrics.csv
prospective_validation_metrics.csv
feature_importance_gain.csv
workflow_agent_audit.json
run_summary.json
```

## Run on a local echocardiography table

Prepare a CSV file using the schema described in `docs/data_schema.md`, then run:

```bash
bav-aorta-agent \
  --input /path/to/local_echo_records.csv \
  --output-dir /path/to/workflow_outputs \
  --validation-start 2026-01-01 \
  --validation-end 2026-03-31
```

The validation window should be adjusted to match the local deployment or temporal validation period.

## Figure generation

Python figure-generation utilities are provided for plots based on workflow CSV outputs. After running the workflow, generate the standard figures with either the installed command-line entry point:

```bash
bav-aorta-plot --output-dir example_outputs_agent --figure-dir figures
```

or the script interface:

```bash
python scripts/plot_figures.py --output-dir example_outputs_agent --figure-dir figures
```

Generated images are written to `figures/`. The plotting code reads only exported CSV summaries and prediction files, so it can be reused after local recalibration or deployment-period validation.

## Model notes

The implemented model is a two-target residual XGBoost workflow. For each target, the model estimates the change from the current examination to the target follow-up examination. The future diameter is reconstructed as:

```text
predicted future diameter = current diameter + predicted diameter change
```

This residual formulation keeps the current aortic measurement as the anatomical anchor and uses body size, blood pressure, valve dysfunction, BAV morphology, Doppler measurements, cardiac dimensions, and follow-up interval to refine the estimated trajectory.

## Local governance

Use local echocardiography records only under applicable institutional approval, data-use permissions, and privacy requirements. Before applying the workflow at a new site, review the schema mapping, morphology labels, preprocessing choices, validation window, and output interpretation with local clinicians.

## Citation

When using this repository, cite the associated manuscript after publication.
