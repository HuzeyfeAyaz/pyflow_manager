import yaml
import networkx as nx
import subprocess
import os
from multiprocessing import Pool


class PyflowManager:
    def __init__(self, yaml_file, num_processes, skip_existing=True):
        self.tasks = self.load_tasks(yaml_file)
        self.num_processes = num_processes
        self.dag = self.create_dag(self.tasks)
        self.dependencies = self.get_dependencies()
        self.skip_existing = skip_existing

    def load_tasks(self, file_path):
        with open(file_path, 'r') as file:
            tasks = yaml.safe_load(file)
        return tasks['tasks']

    def files_exist(self, outputs):
        return all(os.path.exists(output) for output in outputs)

    def create_dag(self, tasks):
        dag = nx.DiGraph()
        for task_name, task_details in tasks.items():
            dag.add_node(task_name)
            for input_file in task_details['inputs']:
                for predecessor, details in tasks.items():
                    if input_file in details['outputs']:
                        dag.add_edge(predecessor, task_name)
        if not nx.is_directed_acyclic_graph(dag):
            raise ValueError("The tasks dependencies do not form a DAG.")
        return dag

    def get_dependencies(self):
        dependencies = {task: set() for task in self.dag.nodes()}
        for task, deps in self.dag.adjacency():
            for dep in deps:
                dependencies[dep].add(task)

        return dependencies

    def is_ready(self, task_name):
        if len(self.dependencies[task_name]) == 0:
            return True
        return all(dep in self.finished_tasks
                   for dep in self.dependencies[task_name])

    def is_failed(self, task_name):
        return any(dep in self.failed_tasks
                   for dep in self.dependencies[task_name])

    def execute_task(self, task_name):
        outputs = self.tasks[task_name]['outputs']
        command = self.tasks[task_name]['command']

        if self.skip_existing and self.files_exist(outputs):
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
        self.finished_tasks = set()
        self.failed_tasks = set()
        tapological_order = list(nx.topological_sort(self.dag))
        n_tasks = len(self.dag.nodes())

        with Pool(self.num_processes) as pool:
            idx = 0
            while len(self.finished_tasks) + len(self.failed_tasks) < n_tasks:
                concurrent_tasks = [i for i in range(idx, n_tasks) if self.is_ready(
                    tapological_order[i]) or self.is_failed(tapological_order[i])]
                print(
                    f"Concurrent tasks: {[tapological_order[i] for i in concurrent_tasks]}")
                results = []
                for task_idx in concurrent_tasks:
                    task_name = tapological_order[task_idx]
                    if self.is_ready(task_name) and not self.is_failed(
                            task_name):
                        results.append(
                            pool.apply_async(
                                self.execute_task, (task_name,)))
                    elif self.is_failed(task_name):
                        print(
                            f"Skipping {task_name} since a dependency failed")
                        self.failed_tasks.add(task_name)

                for result in results:
                    idx += 1
                    finished_task, error = result.get()
                    if error is not None:
                        self.failed_tasks.add(finished_task)
                    else:
                        self.finished_tasks.add(finished_task)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Pyflow Manager")
    parser.add_argument(
        'yaml_file',
        help="Path to the YAML file defining the tasks and dependencies")
    parser.add_argument(
        '--num_processes', default=2, type=int,
        help="Number of processes to use for parallel execution")
    parser.add_argument(
        '--skip-existing', action='store_true',
        help="Skip tasks if their outputs already exist")
    args = parser.parse_args()

    manager = PyflowManager(
        args.yaml_file, args.num_processes, skip_existing=args.skip_existing)
    manager.execute_workflow()


if __name__ == "__main__":
    main()
