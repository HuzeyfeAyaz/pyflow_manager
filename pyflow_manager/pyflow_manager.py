import networkx as nx
from concurrent.futures import ThreadPoolExecutor
from .loader import load_tasks
from .dag import create_dag, get_dependencies
from .executor import PyflowExecutor
from .print_utils import print_dag_ascii, visualize_dag
import os


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

    def execute_workflow(self):
        executor = PyflowExecutor(self.tasks, self.dag, self.dependencies, self.num_workers, self.skip_existing)
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
        'yaml_file',
        help="Path to the YAML file defining the tasks and dependencies")
    parser.add_argument(
        '-n', '--num_workers', default=8, type=int,
        help="Number of workers to use for parallel execution")
    parser.add_argument(
        '-s', '--skip-existing', action='store_true',
        help="Skip tasks if their outputs already exist")
    parser.add_argument(
        '--print-dag', action='store_true',
        help="Print the DAG of task execution order as an ASCII tree and exit.")
    parser.add_argument(
        '--visualize-dag', action='store_true',
        help="Visualize the DAG using NetworkX and matplotlib, saving to a temporary file.")
    parser.add_argument(
        '--output-image', type=str, default=None,
        help="Path to save the DAG visualization image (used with --visualize-dag).")
    parser.add_argument(
        '-t', '--task', type=str, default=None,
        help="Run only the specified task and all its dependencies.")
    args = parser.parse_args()

    manager = PyflowManager(
        args.yaml_file, args.num_workers, skip_existing=args.skip_existing)
    if args.print_dag:
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
    if args.task:
        # Get all dependencies for the specified task
        if args.task not in manager.dag.nodes:
            raise ValueError(f"Task '{args.task}' not found in workflow.")
        # Get all ancestors (dependencies) and the task itself
        sub_nodes = set(nx.ancestors(manager.dag, args.task)) | {args.task}
        sub_dag = manager.dag.subgraph(sub_nodes).copy()
        # Save original dag and dependencies
        manager.dag = sub_dag
        manager.dependencies = get_dependencies(manager.dag)
        manager.tasks = {k: v for k, v in manager.tasks.items() if k in sub_nodes}
    manager.execute_workflow()


if __name__ == "__main__":
    main()
