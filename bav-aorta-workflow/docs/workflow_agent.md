# Workflow agent and skill interface

This repository includes a deterministic workflow agent and a reusable workflow skill for the BAV aortic dimension estimation pipeline.

## Agent interface

The agent is implemented in `src/bav_aorta_workflow/agent.py`. It coordinates the following steps:

1. Schema review
2. Record preparation
3. Current-to-future pair construction
4. Temporal split for deployment-period validation
5. Residual model training
6. Prediction and metric export
7. Audit-log generation

Run it from the command line:

```bash
bav-aorta-agent \
  --input examples/example_echo_records.csv \
  --output-dir example_outputs_agent \
  --validation-start 2026-01-01 \
  --validation-end 2026-03-31
```

Use it from Python:

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

## Skill interface

The packaged skill is implemented in `src/bav_aorta_workflow/skill.py`. It exposes an input specification, output specification, and a single `run()` method.

```python
from bav_aorta_workflow.skill import BAVAortaPredictionSkill

skill = BAVAortaPredictionSkill()
print(skill.describe())
summary = skill.run(
    input_csv="examples/example_echo_records.csv",
    output_dir="example_outputs_skill",
)
```

## Audit log

The agent writes `workflow_agent_audit.json`, which records completed workflow steps and key counts. This file is useful for local review before results are interpreted or transferred to a new site.
