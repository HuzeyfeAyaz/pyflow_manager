import os
import yaml
import time
import subprocess
import networkx as nx
from concurrent.futures import ThreadPoolExecutor


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

    def is_failed(self, task_name):
        return any(dep in self.failed_tasks
                   for dep in self.dependencies[task_name])

    def execute_task(self, task_name):
        inputs = self.tasks[task_name]['inputs']
        outputs = self.tasks[task_name]['outputs']
        command = self.tasks[task_name]['command']

        if self.skip_existing and self.files_exist(outputs):
            print(f"Skipping {task_name} as outputs already exist")
            return task_name

        if not self.files_exist(inputs):
            for dep in self.dependencies[task_name]:
                while dep not in self.result_map:  # to make sure the dependency is executed
                    time.sleep(1)
                self.result_map[dep].result()
                if dep in self.failed_tasks:
                    print(f"Skipping {task_name} since a dependency failed")
                    self.failed_tasks.add(task_name)
                    return task_name

        try:
            print(f"Executing {task_name}: {command}")
            subprocess.run(command, shell=True, check=True)
            if not self.files_exist(outputs):
                # wait for the outputs to be created
                time.sleep(10)
                if not self.files_exist(outputs):
                    raise Exception(f'Outputs are not created due to an error')
            print(f"Finished {task_name}")
            return task_name  # Return task_name
        except (subprocess.CalledProcessError, Exception) as e:
            print(f"Task {task_name} failed with error: {e}")
            self.failed_tasks.add(task_name)
            return task_name  # Return task_name

    def execute_workflow(self):
        self.result_map = {}
        self.failed_tasks = set()
        topological_sort = list(nx.topological_sort(self.dag))

        with ThreadPoolExecutor(self.num_processes) as executor:
            for task in topological_sort:
                self.result_map[task] = executor.submit(
                    self.execute_task, task)

            for result in self.result_map.values():
                result.result()
            print("Done!")


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
