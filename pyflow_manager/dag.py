import networkx as nx

def create_dag(tasks):
    """
    Build a directed acyclic graph (DAG) from the tasks dict.
    Returns a networkx.DiGraph.
    """
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

def get_dependencies(dag):
    """
    Return a dict mapping each task to its set of direct dependencies (predecessors).
    """
    dependencies = {task: set() for task in dag.nodes()}
    for task, deps in dag.adjacency():
        for dep in deps:
            dependencies[dep].add(task)
    return dependencies 