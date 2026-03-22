import sys
sys.path.append('./pyflow_manager')
from loader import load_tasks

# Load and debug the tasks
tasks = load_tasks('tests/test_command_cluster_only.yaml')

print("=== Loaded Tasks ===")
for task_name, task_details in tasks.items():
    print(f"\nTask: {task_name}")
    print(f"  Command: {task_details.get('command', 'N/A')}")
    print(f"  Inputs: {task_details.get('inputs', [])}")
    print(f"  Outputs: {task_details.get('outputs', [])}")