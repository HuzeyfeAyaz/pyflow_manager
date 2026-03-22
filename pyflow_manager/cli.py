import argparse
import os
import sys

# Handle both direct execution and package execution
if __name__ == "__main__" or not __package__:
    from pyflow_manager import PyflowManager
    import networkx as nx
else:
    from .pyflow_manager import PyflowManager
    import networkx as nx


def main():
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
    full_dag = manager.dag.copy()
    if args.task:
        if args.task not in full_dag.nodes:
            raise ValueError(f"Task '{args.task}' not found in workflow.")
        sub_nodes = set(nx.ancestors(full_dag, args.task)) | {args.task}
        print(f"[DEBUG] Tasks in subgraph for '{args.task}':", sub_nodes)
        manager.restrict_to_tasks(sub_nodes)
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
