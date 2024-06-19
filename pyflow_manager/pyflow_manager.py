import yaml
import networkx as nx
import subprocess
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import os


class PyflowManager:
    def __init__(self, yaml_file, skip_existing=True):
        self.tasks = self.load_tasks(yaml_file)
        self.dag = self.create_dag(self.tasks)
        self.skip_existing = skip_existing

    def load_tasks(self, file_path):
        with open(file_path, 'r') as file:
            tasks = yaml.safe_load(file)
        return tasks['tasks']

    def outputs_exist(self, outputs):
        return all(os.path.exists(output) for output in outputs)

    def create_dag(self, tasks):
        dag = nx.DiGraph()
        for task_name, task_details in tasks.items():
            dag.add_node(
                task_name, command=task_details['command'],
                outputs=task_details['outputs'])
            for input_file in task_details['inputs']:
                for predecessor, details in tasks.items():
                    if input_file in details['outputs']:
                        dag.add_edge(predecessor, task_name)
        if not nx.is_directed_acyclic_graph(dag):
            raise ValueError("The tasks dependencies do not form a DAG.")
        return dag

    def execute_task(self, task_name, command, outputs):
        if self.skip_existing and self.outputs_exist(outputs):
            print(f"Skipping {task_name} as outputs already exist")
            return task_name, None
        try:
            print(f"Executing {task_name}: {command}")
            subprocess.run(command, shell=True, check=True)
            print(f"Finished {task_name}")
            return task_name, None  # Return task_name and no error
        except subprocess.CalledProcessError as e:
            print(f"Task {task_name} failed with error: {e}")
            return task_name, e  # Return task_name and the error

    def execute_workflow(self):
        in_degree = {node: 0 for node in self.dag.nodes()}
        for u, v in self.dag.edges():
            in_degree[v] += 1

        queue = deque(
            [node for node in self.dag.nodes() if in_degree[node] == 0])
        with ThreadPoolExecutor() as executor:
            futures = {}
            failed_tasks = set()

            while queue or futures:
                while queue:
                    current = queue.popleft()
                    command = self.dag.nodes[current]['command']
                    outputs = self.dag.nodes[current]['outputs']
                    futures[executor.submit(
                        self.execute_task, current, command, outputs)] = current

                done = as_completed(futures, timeout=None)
                for future in done:
                    completed_task, error = future.result()
                    futures.pop(future)

                    if error:
                        failed_tasks.add(completed_task)

                    if completed_task in failed_tasks:
                        continue

                    for successor in self.dag.successors(completed_task):
                        in_degree[successor] -= 1
                        if in_degree[successor] == 0 and successor not in failed_tasks:
                            queue.append(successor)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Pyflow Manager")
    parser.add_argument(
        'yaml_file',
        help="Path to the YAML file defining the tasks and dependencies")
    parser.add_argument(
        '--skip-existing', action='store_true',
        help="Skip tasks if their outputs already exist")
    args = parser.parse_args()

    manager = PyflowManager(args.yaml_file, skip_existing=args.skip_existing)
    manager.execute_workflow()


if __name__ == "__main__":
    main()
