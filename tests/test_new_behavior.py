#!/usr/bin/env python3

from pyflow_manager.loader import load_tasks
import pprint


def test_parameter_behavior():
    print("Testing new parameter behavior...")

    # Load tasks from test file
    tasks = load_tasks("tests/test_parameter_behavior.yaml")

    print("\nGenerated tasks:")
    for task_name, task_details in tasks.items():
        print(f"\n{task_name}:")
        pprint.pprint(task_details, indent=2)

    print(f"\nTotal number of tasks generated: {len(tasks)}")

    # Verify expected behavior
    expected_command_tasks = [
        "command_param_task_data1fast",
        "command_param_task_data1slow",
        "command_param_task_data2fast",
        "command_param_task_data2slow",
    ]

    print(f"\nExpected command parameter tasks: {expected_command_tasks}")
    print(
        f"Found command parameter tasks: {[t for t in tasks.keys() if t.startswith('command_param_task')]}"
    )

    # Check if io_param_task exists as single task
    if "io_param_task" in tasks:
        print(f"\nio_param_task inputs: {tasks['io_param_task']['inputs']}")
        print(f"io_param_task outputs: {tasks['io_param_task']['outputs']}")
    else:
        print("\nERROR: io_param_task not found!")


if __name__ == "__main__":
    test_parameter_behavior()
