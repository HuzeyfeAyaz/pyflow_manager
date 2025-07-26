# Pyflow Manager

A Python package to manage and execute workflows based on YAML-defined input/output dependencies. Supports advanced features like task output references, DAG visualization, cross-file includes, parameter sweeps, and targeted execution.

## Installation

```bash
pip install pyflow-manager
```

## Features
- **YAML-based workflow definition**
- **Outputs as Inputs:** Reference outputs of other tasks as inputs (e.g., `task1.outputs`)
- **DAG Printing:** Visualize the execution order as an ASCII art tree
- **Include/Import:** Import tasks from other YAML files with `include`
- **Parameter Sweeps:** Use `parameters` to create multiple tasks with all combinations or expand dependencies
- **Run Specific Task:** Execute a specific task and all its dependencies
- **Parallel Execution:** Run tasks in parallel with dependency management

## Usage

```bash
pyflow-manager <path/to/your/tasks.yaml> [options]
```

### CLI Options
| Option                | Description                                                      |
|----------------------|------------------------------------------------------------------|
| `-n, --num_workers`  | Number of workers for parallel execution (default: 8)            |
| `-s, --skip-existing`| Skip tasks if their outputs already exist                         |
| `--print-dag`        | Print the DAG of task execution order as an ASCII tree and exit   |
| `-t, --task`         | Run only the specified task and all its dependencies             |

## Sample YAML File

```yaml
include:
  - included_tasks.yaml

tasks:
  task1:
    command: "echo 'Task 1' > output1.txt"
    inputs: []
    outputs: ["output1.txt"]
  task2:
    command: "echo 'Task 2' > output2.txt"
    inputs: task1.outputs
    outputs: ["output2.txt"]
  sweep_task:
    command: "echo 'Sweep {a} {b}' > sweep_{a}_{b}.txt"
    inputs: []
    outputs: ["sweep_{a}_{b}.txt"]
    parameters:
      a: [1, 2]
      b: [x, y]
```

## Parameter Sweeps

Pyflow Manager supports two types of parameter handling:

### 1. Command Parameter Sweeps
When parameters are used in the `command` field, multiple tasks are created for each parameter combination:

```yaml
tasks:
  sweep_task:
    command: "echo 'Processing {dataset} with {model}' > result_{dataset}_{model}.txt"
    inputs: []
    outputs: ["result_{dataset}_{model}.txt"]
    parameters:
      dataset: [train, test]
      model: [linear, neural]
```

This creates 4 separate tasks:
- `sweep_task_datasettrain_modellinear`
- `sweep_task_datasettrain_modelneural`
- `sweep_task_datasettest_modellinear`
- `sweep_task_datasettest_modelneural`

### 2. Dependency Parameter Expansion
When parameters are only used in `inputs` or `outputs` (not in `command`), a single task is created with expanded dependencies:

```yaml
tasks:
  collect_results:
    command: "python collect.py"
    inputs: ["result_{dataset}_{model}.txt"]
    outputs: ["summary.txt"]
    parameters:
      dataset: [train, test]
      model: [linear, neural]
```

This creates one task `collect_results` with inputs expanded to:
- `result_train_linear.txt`
- `result_train_neural.txt`
- `result_test_linear.txt`
- `result_test_neural.txt`

### included_tasks.yaml
```yaml
tasks:
  task3:
    command: "echo 'Task 3' > output3.txt"
    inputs: task2.outputs
    outputs: ["output3.txt"]
```

## Example: Print the DAG
```bash
python -m pyflow_manager.cli tasks.yaml --print-dag
```

## Example: Run a Specific Task
```bash
python -m pyflow_manager.cli tasks.yaml -t sweep_task_a1_bx
```

## Modular Code Structure
- `pyflow_manager/loader.py` — YAML loading, includes, parameter sweeps, output references
- `pyflow_manager/dag.py` — DAG construction and dependency extraction
- `pyflow_manager/executor.py` — Task execution logic
- `pyflow_manager/print_utils.py` — ASCII DAG printing
- `pyflow_manager/pyflow_manager.py` — Orchestrates the above, main manager class
- `pyflow_manager/cli.py` — CLI entry point and argument parsing

## Reference

Please cite this repo if you used it in your research:
```
Ayaz, H. (no date) HuzeyfeAyaz/pyflow_manager: Python based Parallel Workflow Management System, GitHub. Available at: https://github.com/HuzeyfeAyaz/pyflow_manager (Accessed: 21 June 2024).
```