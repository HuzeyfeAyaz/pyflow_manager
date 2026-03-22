import os
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor


class PyflowExecutor:
    def __init__(
        self, tasks, dag, dependencies, num_workers, skip_existing=True
    ):
        self.tasks = tasks
        self.dag = dag
        self.dependencies = dependencies
        self.num_workers = num_workers
        self.skip_existing = skip_existing

    def files_exist(self, outputs):
        return all(os.path.exists(output) for output in outputs)

    def execute_task(self, task_name):
        # Wait for all dependencies to finish
        for dep in self.dependencies[task_name]:
            if dep in self.result_map:
                self.result_map[dep].result()

        # If any dependency failed, skip this task (do this before any file existence checks)
        if any(
            dep in self.failed_tasks for dep in self.dependencies[task_name]
        ):
            print(f"Skipping {task_name} since a dependency failed")
            self.failed_tasks.add(task_name)
            return task_name

        inputs = self.tasks[task_name]["inputs"]
        outputs = self.tasks[task_name]["outputs"]
        command = self.tasks[task_name]["command"]

        # If any input is missing, skip this task
        if not self.files_exist(inputs):
            print(f"Skipping {task_name} since required inputs are missing")
            self.failed_tasks.add(task_name)
            return task_name

        if self.skip_existing and self.files_exist(outputs):
            print(f"Skipping {task_name} as outputs already exist")
            return task_name

        if not self.files_exist(inputs):
            for dep in self.dependencies[task_name]:
                while (
                    dep not in self.result_map
                ):  # to make sure the dependency is executed
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
                    raise Exception(f"Outputs are not created due to an error")
            print(f"Finished {task_name}")
            return task_name  # Return task_name
        except (subprocess.CalledProcessError, Exception) as e:
            print(f"Task {task_name} failed with error: {e}")
            self.failed_tasks.add(task_name)
            # Delete outputs if task fails
            for output in outputs:
                if os.path.exists(output):
                    os.remove(output)
            return task_name  # Return task_name

    def execute_workflow(self):
        self.result_map = {}
        self.failed_tasks = set()
        import networkx as nx

        topological_sort = list(nx.topological_sort(self.dag))

        with ThreadPoolExecutor(self.num_workers) as executor:
            for task in topological_sort:
                self.result_map[task] = executor.submit(
                    self.execute_task, task
                )

            for result in self.result_map.values():
                result.result()
            print("Done!")
