import os
import yaml
import itertools

def load_tasks(file_path, loaded_files=None, resolve_references=True) -> dict:
    """
    Load tasks from a YAML file, handling includes and parameter sweeps.
    Returns a dict of task_name -> task_details.
    'taskX.outputs' references are resolved in a second pass after all tasks are merged (only in the top-level call).
    """
    if loaded_files is None:
        loaded_files = set()
    if file_path in loaded_files:
        raise ValueError(f"Cyclic or duplicate include detected for file: {file_path}")
        return {}
    loaded_files.add(file_path)
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
    tasks = {}
    # Handle includes (merge all tasks first)
    if 'include' in data:
        include_files = data['include']
        if isinstance(include_files, str):
            include_files = [include_files]
        for inc_file in include_files:
            inc_path = os.path.join(os.path.dirname(file_path), inc_file)
            inc_tasks = load_tasks(inc_path, loaded_files, resolve_references=False)
            for tname in inc_tasks:
                if tname in tasks:
                    raise ValueError(f"Duplicate task name '{tname}' found in included file '{inc_file}'")
            tasks.update(inc_tasks)
    # Load this file's tasks
    for tname, tdetails in data.get('tasks', {}).items():
        if tname in tasks:
            raise ValueError(f"Duplicate task name '{tname}' found in file '{file_path}'")
        # Parameter sweep expansion
        if 'parameters' in tdetails:
            param_dict = tdetails['parameters']
            keys = list(param_dict.keys())
            values = list(param_dict.values())
            for combo in itertools.product(*values):
                param_map = dict(zip(keys, combo))
                combo_str = "_".join(f"{k}{v}" for k, v in param_map.items())
                expanded_name = f"{tname}_{combo_str}"
                if expanded_name in tasks:
                    raise ValueError(f"Duplicate expanded task name '{expanded_name}' from parameters in '{tname}'")
                def subst(val):
                    if isinstance(val, str):
                        return val.format(**param_map)
                    elif isinstance(val, list):
                        return [subst(x) for x in val]
                    else:
                        return val
                expanded_task = {
                    k: subst(v) if k in ['command', 'inputs', 'outputs'] else v
                    for k, v in tdetails.items() if k != 'parameters'
                }
                tasks[expanded_name] = expanded_task
        else:
            tasks[tname] = tdetails
    # Only resolve references in the top-level call
    if resolve_references:
        for task_name, task_details in tasks.items():
            # Ensure inputs is always a list
            if isinstance(task_details['inputs'], str):
                task_details['inputs'] = [task_details['inputs']]
            resolved_inputs = []
            for inp in task_details['inputs']:
                if isinstance(inp, str) and inp.endswith('.outputs'):
                    ref_task = inp[:-8]  # remove '.outputs'
                    if ref_task not in tasks:
                        raise ValueError(f"Task '{task_name}' references unknown task '{ref_task}' in inputs.")
                    resolved_inputs.extend(tasks[ref_task]['outputs'])
                elif isinstance(inp, list):
                    for subinp in inp:
                        if isinstance(subinp, str) and subinp.endswith('.outputs'):
                            ref_task = subinp[:-8]
                            if ref_task not in tasks:
                                raise ValueError(f"Task '{task_name}' references unknown task '{ref_task}' in inputs.")
                            resolved_inputs.extend(tasks[ref_task]['outputs'])
                        else:
                            resolved_inputs.append(subinp)
                else:
                    resolved_inputs.append(inp)
            task_details['inputs'] = resolved_inputs
    return tasks 