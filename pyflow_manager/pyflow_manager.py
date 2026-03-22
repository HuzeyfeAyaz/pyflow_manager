import networkx as nx
from concurrent.futures import ThreadPoolExecutor
import os
import sys

# Handle both direct execution and package execution
if __name__ == "__main__" or not __package__:
    from loader import load_tasks
    from dag import create_dag, get_dependencies
    from executor import PyflowExecutor
    from print_utils import print_dag_ascii, visualize_dag
else:
    from .loader import load_tasks
    from .dag import create_dag, get_dependencies
    from .executor import PyflowExecutor
    from .print_utils import print_dag_ascii, visualize_dag


class PyflowManager:
    def __init__(self, yaml_file, num_workers, skip_existing=True):
        self.tasks = load_tasks(yaml_file)
        self.num_workers = num_workers
        self.dag = create_dag(self.tasks)
        self.dependencies = get_dependencies(self.dag)
        self.skip_existing = skip_existing

    def restrict_to_tasks(self, task_names):
        """
        Restrict the workflow to a subgraph containing only the specified task names.
        Updates self.dag, self.dependencies, and self.tasks accordingly.
        """
        self.dag = self.dag.subgraph(task_names).copy()
        self.dependencies = get_dependencies(self.dag)
        self.tasks = {k: v for k, v in self.tasks.items() if k in task_names}

    def get_executable_tasks(self):
        """
        Get the subset of tasks that should be executed based on skip_existing setting.
        If skip_existing is True, filters out tasks whose outputs already exist.
        """
        if not self.skip_existing:
            return set(self.tasks.keys())

        executable_tasks = set()
        for task_name, task_details in self.tasks.items():
            outputs = task_details.get("outputs", [])
            # Check if any output file is missing
            if not all(os.path.exists(output) for output in outputs):
                executable_tasks.add(task_name)

        return executable_tasks

    def filter_dag_for_execution(self):
        """
        Filter the DAG to include only tasks that should be executed.
        """
        executable_tasks = self.get_executable_tasks()
        # Also include dependencies of executable tasks
        import networkx as nx

        tasks_to_include = set()
        for task in executable_tasks:
            tasks_to_include.add(task)
            # Add all ancestors (dependencies) of this task
            tasks_to_include.update(nx.ancestors(self.dag, task))

        self.restrict_to_tasks(tasks_to_include)

    def execute_workflow(self):
        executor = PyflowExecutor(
            self.tasks,
            self.dag,
            self.dependencies,
            self.num_workers,
            self.skip_existing,
        )
        executor.execute_workflow()

    def print_dag_ascii(self):
        print_dag_ascii(self.dag)

    def visualize_dag(self, output_path=None):
        """
        Visualize the DAG using NetworkX and matplotlib.

        Args:
            output_path: Optional path to save the image. If None, saves to a temporary file.

        Returns:
            Path to the saved image.
        """
        return visualize_dag(self.dag, output_path)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Pyflow Manager")
    parser.add_argument(
        "yaml_file",
        help="Path to the YAML file defining the tasks and dependencies",
    )
    parser.add_argument(
        "-n",
        "--num_workers",
        default=8,
        type=int,
        help="Number of workers to use for parallel execution",
    )
    parser.add_argument(
        "-s",
        "--skip-existing",
        action="store_true",
        help="Skip tasks if their outputs already exist",
    )
    parser.add_argument(
        "--print-dag",
        action="store_true",
        help="Print the DAG of task execution order as an ASCII tree and exit.",
    )
    parser.add_argument(
        "--visualize-dag",
        action="store_true",
        help="Visualize the DAG using NetworkX and matplotlib, saving to a temporary file.",
    )
    parser.add_argument(
        "--output-image",
        type=str,
        default=None,
        help="Path to save the DAG visualization image (used with --visualize-dag).",
    )
    parser.add_argument(
        "-t",
        "--task",
        type=str,
        default=None,
        help="Run only the specified task and all its dependencies.",
    )
    args = parser.parse_args()

    manager = PyflowManager(
        args.yaml_file, args.num_workers, skip_existing=args.skip_existing
    )
    if args.task:
        # Get all dependencies for the specified task
        # Check if the exact task name exists
        if args.task in manager.dag.nodes:
            # Exact match found
            target_task = args.task
        else:
            # Check if any task names start with the specified task name (for parameterized tasks)
            matching_tasks = [
                task
                for task in manager.dag.nodes
                if task.startswith(args.task + "_")
            ]
            if matching_tasks:
                # Use the first matching task to find dependencies, but include all matching tasks
                target_task = matching_tasks[0]
                # Include all matching tasks in the subgraph
                sub_nodes = set()
                for task in matching_tasks:
                    sub_nodes.update(nx.ancestors(manager.dag, task))
                sub_nodes.update(matching_tasks)
            else:
                raise ValueError(f"Task '{args.task}' not found in workflow.")

        # If we didn't set target_task and sub_nodes already, do the normal processing
        if "target_task" not in locals() and "sub_nodes" not in locals():
            # Get all ancestors (dependencies) and the task itself
            sub_nodes = set(nx.ancestors(manager.dag, args.task)) | {args.task}

        sub_dag = manager.dag.subgraph(sub_nodes).copy()
        # Save original dag and dependencies
        manager.dag = sub_dag
        manager.dependencies = get_dependencies(manager.dag)
        manager.tasks = {
            k: v for k, v in manager.tasks.items() if k in sub_nodes
        }
    if args.print_dag:
        # If skip_existing is enabled, filter the DAG to show only tasks that will be executed
        if args.skip_existing:
            manager.filter_dag_for_execution()
        manager.print_dag_ascii()
        return
    if args.visualize_dag:
        output_path = args.output_image
        if output_path and not os.path.isabs(output_path):
            # Convert relative path to absolute
            output_path = os.path.abspath(output_path)
        image_path = manager.visualize_dag(output_path)
        print(f"DAG visualization saved to: {image_path}")
        return
    manager.execute_workflow()


if __name__ == "__main__":
    main()
