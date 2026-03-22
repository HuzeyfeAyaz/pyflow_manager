import os
import yaml
import itertools
import re
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
            for inc_file in include_files:
                # Handle relative paths properly
                if os.path.isabs(inc_file):
                    include_path = inc_file
                    include_base_dir = os.path.dirname(inc_file)
                else:
                    include_path = os.path.join(base_dir, inc_file)
                    include_base_dir = os.path.dirname(include_path)

                files_to_process.append((include_path, include_base_dir))

        # Process tasks from current file
        for task_name, task_details in data.get("tasks", {}).items():
            if task_name in tasks:
                raise ValueError(
                    f"Duplicate task name '{task_name}' found in file '{current_file}'"
                )

            # Don't process Python expressions initially - let parameter substitution happen first
            tasks.update(_process_task_parameters(task_name, task_details))

    if resolve_references:
        _resolve_task_references(tasks)

    return tasks


def _process_python_expressions(value: Any) -> Any:
    """
    Process any value, executing Python code found in double curly brackets {{}}.

    Args:
        value: The value to process (can be string, dict, list, or any other type)

    Returns:
        The processed value, with Python code in {{}} executed
    """
    if isinstance(value, str):
        # Check if the value contains Python code in double curly brackets
        pattern = r"\{\{(.+?)\}\}"
        matches = re.findall(pattern, value)

        if matches:
            # If the entire string is just one Python expression, return the evaluated result
            if len(matches) == 1 and value.strip() == f"{{{{{matches[0]}}}}}":
                try:
                    return eval(matches[0])
                except Exception as e:
                    raise ValueError(
                        f"Error executing Python code '{matches[0]}': {e}"
                    )
            else:
                # If there are multiple expressions or the string contains other text,
                # replace each expression with its result
                result = value
                for match in matches:
                    try:
                        replacement = str(eval(match))
                        result = result.replace(
                            f"{{{{{match}}}}}", replacement
                        )
                    except Exception as e:
                        raise ValueError(
                            f"Error executing Python code '{match}': {e}"
                        )
                return result
        return value
    elif isinstance(value, dict):
        # Recursively process dictionary values
        return {k: _process_python_expressions(v) for k, v in value.items()}
    elif isinstance(value, list):
        # Recursively process list items
        return [_process_python_expressions(item) for item in value]
    else:
        # Return other types as-is
        return value


def _process_task_parameters(
    task_name: str, task_details: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """Process a single task, handling parameter expansion."""
    if "parameters" not in task_details:
        # No parameters, but still need to process Python expressions in other fields
        processed_task = {}
        for key, value in task_details.items():
            processed_task[key] = _process_python_expressions(value)
        return {task_name: processed_task}

    param_dict = task_details["parameters"]
    # Process Python expressions in parameter values first
    processed_param_dict = {}
    for key, value in param_dict.items():
        processed_value = _process_python_expressions(value)
        # Ensure parameter values are lists for iteration
        if not isinstance(processed_value, list):
            processed_value = [processed_value]
        processed_param_dict[key] = processed_value

    param_keys = list(processed_param_dict.keys())
    param_values = list(processed_param_dict.values())

    # Check which parameters are actually used in the command
    command = task_details.get("command", "")
    params_used_in_command = set()
    if isinstance(command, str):
        for key in param_keys:
            if f"{{{key}}}" in command:
                params_used_in_command.add(key)

    if params_used_in_command:
        # Generate separate tasks based on command parameters
        # Use only the parameters that are actually used in the command
        command_param_keys = list(params_used_in_command)
        command_param_values = [processed_param_dict[key] for key in command_param_keys]
        
        return _generate_parameter_tasks(
            task_name, task_details, param_keys, param_values, command_param_keys
        )
    else:
        # No parameters used in command, expand all as dependencies
        return _expand_parameter_dependencies(
            task_name, task_details, param_keys, param_values
        )


def _generate_parameter_tasks(
    task_name: str,
    task_details: Dict[str, Any],
    all_param_keys: List[str],
    all_param_values: List[List[Any]],
    command_param_keys: List[str],
) -> Dict[str, Dict[str, Any]]:
    """Generate separate tasks for each parameter combination when command uses parameters."""
    tasks = {}

    # Get indices of command parameters in all parameters
    command_param_indices = [all_param_keys.index(key) for key in command_param_keys]
    command_param_values = [all_param_values[i] for i in command_param_indices]

    # Iterate only through command parameter combinations
    for command_combo in itertools.product(*command_param_values):
        # Create parameter map for command substitution
        command_param_map = dict(zip(command_param_keys, command_combo))
        
        # Create task name based on command parameters only
        combo_str = "_".join(f"{k}{v}" for k, v in command_param_map.items())
        expanded_name = f"{task_name}_{combo_str}"

        if expanded_name in tasks:
            raise ValueError(
                f"Duplicate expanded task name '{expanded_name}' from parameters in '{task_name}'"
            )

        expanded_task = {}
        for key, value in task_details.items():
            if key == "parameters":
                continue
            elif key == "command":
                # For command, substitute only command parameters
                expanded_task[key] = _substitute_parameters(value, command_param_map)
            elif key in {"inputs", "outputs"}:
                # For inputs/outputs, handle mixed parameters correctly
                expanded_task[key] = _handle_mixed_parameters(
                    value, command_param_map, all_param_keys, all_param_values
                )
            else:
                expanded_task[key] = value

        tasks[expanded_name] = expanded_task

    return tasks


def _handle_mixed_parameters(value, command_param_map, all_param_keys, all_param_values):
    """Handle inputs/outputs that may contain both command and non-command parameters."""
    if isinstance(value, list):
        result = []
        for item in value:
            processed_item = _handle_mixed_parameters(
                item, command_param_map, all_param_keys, all_param_values
            )
            if isinstance(processed_item, list):
                result.extend(processed_item)
            else:
                result.append(processed_item)
        return result
    elif isinstance(value, str):
        # Check which parameters appear in this string
        params_in_string = []
        for param_key in all_param_keys:
            if f"{{{param_key}}}" in value:
                params_in_string.append(param_key)
        
        if not params_in_string:
            # No parameters, just process Python expressions
            return _process_python_expressions(value)
        
        # Separate command and non-command parameters
        command_params_in_string = [p for p in params_in_string if p in command_param_map]
        non_command_params_in_string = [p for p in params_in_string if p not in command_param_map]
        
        if not non_command_params_in_string:
            # Only command parameters, substitute directly
            return _substitute_parameters(value, command_param_map)
        elif not command_params_in_string:
            # Only non-command parameters, expand all combinations
            non_command_indices = [all_param_keys.index(p) for p in non_command_params_in_string]
            non_command_values = [all_param_values[i] for i in non_command_indices]
            
            result = []
            for combo in itertools.product(*non_command_values):
                param_map = dict(zip(non_command_params_in_string, combo))
                # Also include command parameters
                full_param_map = {**command_param_map, **param_map}
                substituted = value.format(**full_param_map)
                processed = _process_python_expressions(substituted)
                result.append(processed)
            return result
        else:
            # Mixed parameters - this is complex, expand non-command and substitute command
            non_command_indices = [all_param_keys.index(p) for p in non_command_params_in_string]
            non_command_values = [all_param_values[i] for i in non_command_indices]
            
            result = []
            for combo in itertools.product(*non_command_values):
                param_map = dict(zip(non_command_params_in_string, combo))
                # Also include command parameters
                full_param_map = {**command_param_map, **param_map}
                substituted = value.format(**full_param_map)
                processed = _process_python_expressions(substituted)
                result.append(processed)
            return result
    else:
        return _process_python_expressions(value)


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
    """Substitute parameters in a value recursively, then process Python expressions."""
    if isinstance(value, str):
        # First substitute parameters using manual replacement
        substituted = value
        for param, val in param_map.items():
            placeholder = f"{{{param}}}"
            substituted = substituted.replace(placeholder, str(val))
        # Then process Python expressions
        return _process_python_expressions(substituted)
    elif isinstance(value, list):
        return [_substitute_parameters(item, param_map) for item in value]
    else:
        return value


def _expand_dependencies(
    value: Any, param_keys: List[str], param_values: List[List[Any]]
) -> Any:
    """Expand dependencies that contain parameter placeholders and process Python expressions."""
    if isinstance(value, str):
        if any(f"{{{key}}}" in value for key in param_keys):
            expanded_list = []
            for combo in itertools.product(*param_values):
                param_map = dict(zip(param_keys, combo))
                substituted = value.format(**param_map)
                # Process Python expressions after parameter substitution
                processed = _process_python_expressions(substituted)
                expanded_list.append(processed)
            return expanded_list
        else:
            # No parameters to expand, but still process Python expressions
            return _process_python_expressions(value)
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
        # Process Python expressions for non-string, non-list values too
        return _process_python_expressions(value)


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
