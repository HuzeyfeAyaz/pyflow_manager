#!/usr/bin/env python3
"""
Test script to verify that the skip_existing parameter works correctly with --print-dag.
"""
import os
import tempfile
import shutil
from pyflow_manager.pyflow_manager import PyflowManager


def test_skip_existing_with_print_dag():
    """Test that --print-dag shows only executable tasks when -s is used."""

    # Create a temporary test directory
    test_dir = tempfile.mkdtemp()
    print(f"Test directory: {test_dir}")

    try:
        # Create a simple test YAML file
        yaml_content = """
tasks:
  task1:
    command: "echo 'Task 1' > output1.txt"
    inputs: []
    outputs: ["output1.txt"]
  task2:
    command: "echo 'Task 2' > output2.txt"
    inputs: ["output1.txt"]
    outputs: ["output2.txt"]
  task3:
    command: "echo 'Task 3' > output3.txt"
    inputs: []
    outputs: ["output3.txt"]
"""

        yaml_file = os.path.join(test_dir, "test_tasks.yaml")
        with open(yaml_file, "w") as f:
            f.write(yaml_content)

        # Test 1: First run, all tasks should be executable
        print(
            "\n=== Test 1: All tasks should be shown (no existing outputs) ==="
        )
        manager = PyflowManager(yaml_file, 2, skip_existing=True)

        # Before running, check if outputs exist
        print("Before running:")
        for task_name, task_details in manager.tasks.items():
            outputs = task_details.get("outputs", [])
            for output in outputs:
                exists = os.path.exists(os.path.join(test_dir, output))
                print(
                    f"  {task_name} output {output}: {'exists' if exists else 'missing'}"
                )

        # Test print-dag without skip_existing (should show all)
        print("\n--- Without skip_existing filter ---")
        manager_copy = PyflowManager(yaml_file, 2, skip_existing=False)
        manager_copy.print_dag_ascii()

        # Test print-dag with skip_existing (should show all since no outputs exist)
        print("\n--- With skip_existing filter ---")
        manager_copy2 = PyflowManager(yaml_file, 2, skip_existing=True)
        manager_copy2.filter_dag_for_execution()
        manager_copy2.print_dag_ascii()

        print(f"\nExecutable tasks: {manager.get_executable_tasks()}")

        # Now run the workflow to create outputs
        print("\n=== Running workflow to create outputs ===")
        os.chdir(test_dir)  # Change to test directory for file creation
        manager.execute_workflow()

        # Test 2: Second run, some tasks should be skipped
        print(
            "\n=== Test 2: Some tasks should be skipped (outputs already exist) ==="
        )
        print("After running:")
        for task_name, task_details in manager.tasks.items():
            outputs = task_details.get("outputs", [])
            for output in outputs:
                exists = os.path.exists(output)
                print(
                    f"  {task_name} output {output}: {'exists' if exists else 'missing'}"
                )

        # Create a new manager to test filtering
        manager2 = PyflowManager(yaml_file, 2, skip_existing=True)
        print(
            f"\nExecutable tasks (should be empty since all outputs exist): {manager2.get_executable_tasks()}"
        )

        # Test print-dag with skip_existing (should show nothing or just dependencies)
        print("\n--- With skip_existing filter after outputs exist ---")
        manager2.filter_dag_for_execution()
        print(f"Tasks after filtering: {list(manager2.tasks.keys())}")
        manager2.print_dag_ascii()

    finally:
        # Clean up
        os.chdir("/ari/users/hayaz")
        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")


def test_include_functionality():
    """Test that the include functionality works correctly."""

    # Create a temporary test directory
    test_dir = tempfile.mkdtemp()
    print(f"Test directory: {test_dir}")

    try:
        # Create the main YAML file with include
        main_yaml = """
include:
  - included_tasks.yaml
tasks:
  main_task:
    command: "echo 'Main task' > main_output.txt"
    inputs: ["included_task.outputs"]
    outputs: ["main_output.txt"]
"""

        # Create the included YAML file
        included_yaml = """
tasks:
  included_task:
    command: "echo 'Included task' > included_output.txt"
    inputs: []
    outputs: ["included_output.txt"]
"""

        main_file = os.path.join(test_dir, "main.yaml")
        included_file = os.path.join(test_dir, "included_tasks.yaml")

        with open(main_file, "w") as f:
            f.write(main_yaml)

        with open(included_file, "w") as f:
            f.write(included_yaml)

        print("\n=== Testing include functionality ===")
        manager = PyflowManager(main_file, 2)

        print(f"Loaded tasks: {list(manager.tasks.keys())}")
        print("Expected: main_task, included_task")

        # Test that both tasks are loaded
        expected_tasks = {"main_task", "included_task"}
        actual_tasks = set(manager.tasks.keys())

        if expected_tasks == actual_tasks:
            print("✓ Include functionality works correctly!")
        else:
            print(
                f"✗ Include functionality failed! Expected {expected_tasks}, got {actual_tasks}"
            )

        # Test DAG creation
        print("\nDAG structure:")
        manager.print_dag_ascii()

    finally:
        # Clean up
        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")


if __name__ == "__main__":
    print("Testing pyflow_manager fixes...")
    test_skip_existing_with_print_dag()
    test_include_functionality()
    print("\nAll tests completed!")
