import os
import yaml
import itertools
from typing import Dict, List, Any, Union


def load_tasks(
    file_path: str, resolve_references: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    Load tasks from a YAML file, handling includes and parameter sweeps.
    Returns a dict of task_name -> task_details.
    'taskX.outputs' references are resolved in a second pass after all tasks are merged.
    """
    tasks = {}
    loaded_files = set()
    files_to_process = [(file_path, os.path.dirname(file_path))]

    # Constants for better performance
    SUBSTITUTABLE_FIELDS = {"command", "inputs", "outputs"}
    OUTPUTS_SUFFIX = ".outputs"

    while files_to_process:
        current_file, base_dir = files_to_process.pop(0)

        if current_file in loaded_files:
            raise ValueError(
                f"Cyclic or duplicate include detected for file: {current_file}"
            )
        loaded_files.add(current_file)

        with open(current_file, "r") as file:
            data = yaml.safe_load(file)

        # Handle includes - add to processing queue
        include_files = data.get("include")
        if include_files:
            if isinstance(include_files, str):
                include_files = [include_files]
            files_to_process.extend(
                (
                    os.path.join(base_dir, inc_file),
                    os.path.dirname(os.path.join(base_dir, inc_file)),
                )
                for inc_file in include_files
            )

        # Process tasks from current file
        for task_name, task_details in data.get("tasks", {}).items():
            if task_name in tasks:
                raise ValueError(
                    f"Duplicate task name '{task_name}' found in file '{current_file}'"
                )

            tasks.update(_process_task_parameters(task_name, task_details))

    if resolve_references:
        _resolve_task_references(tasks)

    return tasks


def _process_task_parameters(
    task_name: str, task_details: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """Process a single task, handling parameter expansion."""
    if "parameters" not in task_details:
        return {task_name: task_details}

    param_dict = task_details["parameters"]
    param_keys = list(param_dict.keys())
    param_values = list(param_dict.values())

    # Check if parameters are used in command
    command = task_details.get("command", "")
    command_uses_params = isinstance(command, str) and any(
        f"{{{key}}}" in command for key in param_keys
    )

    if command_uses_params:
        return _generate_parameter_tasks(
            task_name, task_details, param_keys, param_values
        )
    else:
        return _expand_parameter_dependencies(
            task_name, task_details, param_keys, param_values
        )


def _generate_parameter_tasks(
    task_name: str,
    task_details: Dict[str, Any],
    param_keys: List[str],
    param_values: List[List[Any]],
) -> Dict[str, Dict[str, Any]]:
    """Generate separate tasks for each parameter combination when command uses parameters."""
    tasks = {}

    for combo in itertools.product(*param_values):
        param_map = dict(zip(param_keys, combo))
        combo_str = "_".join(f"{k}{v}" for k, v in param_map.items())
        expanded_name = f"{task_name}_{combo_str}"

        if expanded_name in tasks:
            raise ValueError(
                f"Duplicate expanded task name '{expanded_name}' from parameters in '{task_name}'"
            )

        expanded_task = {}
        for key, value in task_details.items():
            if key == "parameters":
                continue
            elif key in {"command", "inputs", "outputs"}:
                expanded_task[key] = _substitute_parameters(value, param_map)
            else:
                expanded_task[key] = value

        tasks[expanded_name] = expanded_task

    return tasks


def _expand_parameter_dependencies(
    task_name: str,
    task_details: Dict[str, Any],
    param_keys: List[str],
    param_values: List[List[Any]],
) -> Dict[str, Dict[str, Any]]:
    """Create single task with expanded input/output dependencies."""
    expanded_task = {}

    for key, value in task_details.items():
        if key == "parameters":
            continue
        elif key in {"inputs", "outputs"}:
            expanded_task[key] = _expand_dependencies(
                value, param_keys, param_values
            )
        else:
            expanded_task[key] = value

    return {task_name: expanded_task}


def _substitute_parameters(value: Any, param_map: Dict[str, Any]) -> Any:
    """Substitute parameters in a value recursively."""
    if isinstance(value, str):
        return value.format(**param_map)
    elif isinstance(value, list):
        return [_substitute_parameters(item, param_map) for item in value]
    else:
        return value


def _expand_dependencies(
    value: Any, param_keys: List[str], param_values: List[List[Any]]
) -> Any:
    """Expand dependencies that contain parameter placeholders."""
    if isinstance(value, str):
        if any(f"{{{key}}}" in value for key in param_keys):
            return [
                value.format(**dict(zip(param_keys, combo)))
                for combo in itertools.product(*param_values)
            ]
        return value
    elif isinstance(value, list):
        expanded_list = []
        for item in value:
            expanded_item = _expand_dependencies(
                item, param_keys, param_values
            )
            if isinstance(expanded_item, list):
                expanded_list.extend(expanded_item)
            else:
                expanded_list.append(expanded_item)
        return expanded_list
    else:
        return value


def _resolve_task_references(tasks: Dict[str, Dict[str, Any]]) -> None:
    """Resolve task.outputs references in inputs."""
    for task_name, task_details in tasks.items():
        # Ensure inputs is always a list
        inputs = task_details.get("inputs", [])
        if isinstance(inputs, str):
            inputs = [inputs]
            task_details["inputs"] = inputs

        resolved_inputs = []
        for inp in inputs:
            if isinstance(inp, str) and inp.endswith(".outputs"):
                ref_task = inp[:-8]  # remove '.outputs'
                if ref_task not in tasks:
                    raise ValueError(
                        f"Task '{task_name}' references unknown task '{ref_task}' in inputs."
                    )
                resolved_inputs.extend(tasks[ref_task]["outputs"])
            elif isinstance(inp, list):
                for subinp in inp:
                    if isinstance(subinp, str) and subinp.endswith(".outputs"):
                        ref_task = subinp[:-8]
                        if ref_task not in tasks:
                            raise ValueError(
                                f"Task '{task_name}' references unknown task '{ref_task}' in inputs."
                            )
                        resolved_inputs.extend(tasks[ref_task]["outputs"])
                    else:
                        resolved_inputs.append(subinp)
            else:
                resolved_inputs.append(inp)

        task_details["inputs"] = resolved_inputs
