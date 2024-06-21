# Pyflow Manager

A Python package to manage and execute workflows based on YAML-defined input/output dependencies.

## Installation

```bash
pip install pyflow-manager
```

## Usage

```bash
pyflow-manager <path/to/your/tasks.yaml> --skip-existing
```

## Sample .yaml File

```yaml
tasks:
    task1:
        command: "echo 'Task 1' > output1.txt"
        inputs: []
        outputs: ["output1.txt"]
    task2:
        command: "python sample_script.py" # generates output2.txt
        inputs: ["output1.txt"]
        outputs: ["output2.txt"]
    task3:
        command: "sbatch -W slurm_script.sh" # Sample Slurm usage. Use -W to wait for the job execution
        inputs: ["output2.txt"]
        outputs: ["output3.txt"]
```