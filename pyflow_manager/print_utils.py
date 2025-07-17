import networkx as nx
import matplotlib.pyplot as plt
import os
import tempfile
import numpy as np
import math
import matplotlib.patches as mpatches


def print_dag_ascii(dag):
    """
    Print the DAG as an ASCII art tree, showing dependencies.
    """
    roots = [n for n in dag.nodes if dag.in_degree(n) == 0]
    visited = set()

    def print_tree(node, prefix="", is_last=True):
        print(prefix + ("└── " if is_last else "├── ") + node)
        visited.add(node)
        children = list(dag.successors(node))
        for i, child in enumerate(children):
            is_last_child = i == len(children) - 1
            print_tree(
                child, prefix + ("    " if is_last else "│   "), is_last_child
            )

    for i, root in enumerate(roots):
        is_last_root = i == len(roots) - 1
        print_tree(root, "", is_last_root)


def visualize_dag(dag, output_path=None):
    """
    Visualize the DAG using NetworkX and matplotlib with enhanced styling.

    Args:
        dag: NetworkX DiGraph object representing the workflow DAG
        output_path: Optional path to save the image. If None, displays the graph.

    Returns:
        Path to the saved image if output_path is provided, None otherwise.
    """
    # Set up figure with a clean, modern style
    plt.figure(figsize=(14, 10), facecolor="white", dpi=150)

    # Group nodes by their level in the graph for better layout
    node_depths = {}
    roots = [n for n in dag.nodes if dag.in_degree(n) == 0]

    # Calculate node depths using BFS
    for root in roots:
        bfs_edges = list(nx.bfs_edges(dag, root))
        nodes = [root] + [v for _, v in bfs_edges]
        for i, node in enumerate(nodes):
            if node not in node_depths or i < node_depths[node]:
                node_depths[node] = i

    # Group nodes by depth for better visualization
    nodes_by_depth = {}
    for node, depth in node_depths.items():
        if depth not in nodes_by_depth:
            nodes_by_depth[depth] = []
        nodes_by_depth[depth].append(node)

    # Create a custom layout based on node depth
    pos = {}
    max_depth = max(node_depths.values()) if node_depths else 0

    # Adjust these parameters for better spacing
    horizontal_spacing = 1.0
    vertical_spacing = 1.5

    # Position nodes by depth with even horizontal spacing
    for depth, nodes in nodes_by_depth.items():
        num_nodes = len(nodes)
        for i, node in enumerate(nodes):
            # Center nodes horizontally within their depth level
            if num_nodes > 1:
                x_pos = (i - (num_nodes - 1) / 2) * horizontal_spacing
            else:
                x_pos = 0

            # Add some jitter to separate nodes better
            jitter = (hash(node) % 100) / 500.0
            pos[node] = (x_pos + jitter, -depth * vertical_spacing)

    # If there are isolated nodes, position them separately
    isolated = [n for n in dag.nodes if dag.degree(n) == 0]
    if isolated:
        iso_x = (
            -max(len(nodes) for nodes in nodes_by_depth.values())
            * horizontal_spacing
            / 2
        )
        for i, node in enumerate(isolated):
            pos[node] = (iso_x, -(i + 1) * vertical_spacing)

    # Create a custom colormap for nodes based on depth
    max_depth = max(node_depths.values()) if node_depths else 0
    cmap = plt.cm.viridis
    node_colors = []

    # Create a more meaningful color scheme based on node type
    regular_tasks = []
    sweep_tasks = []

    for node in dag.nodes():
        depth = node_depths.get(node, 0)
        # Use different color ranges for different node types
        if "sweep_task" in node:
            # Use blues for sweep tasks
            color_val = 0.7  # Blue-ish in viridis
            sweep_tasks.append(node)
        else:
            # Use greens to purples for regular tasks based on depth
            color_val = 0.2 + 0.5 * depth / max(max_depth, 1)
            regular_tasks.append(node)
        node_colors.append(cmap(color_val))

    # Draw edges with a slight curve and better styling
    nx.draw_networkx_edges(
        dag,
        pos,
        width=1.5,
        alpha=0.8,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=15,
        edge_color="dimgray",
        connectionstyle="arc3,rad=0.1",  # Slightly curved edges
    )

    # Calculate node sizes based on their importance (number of connections)
    node_sizes = []
    for node in dag.nodes():
        # Size based on total connections (in + out)
        connections = dag.in_degree(node) + dag.out_degree(node)
        size = (
            2000 + connections * 300
        )  # Base size + additional size per connection
        node_sizes.append(size)

    # Draw nodes with a modern style
    nodes = nx.draw_networkx_nodes(
        dag,
        pos,
        node_size=node_sizes,
        node_color=node_colors,
        edgecolors="white",
        linewidths=2.0,
        alpha=0.9,
    )

    # Add a subtle shadow effect to nodes
    if hasattr(nodes, "set_edgecolor"):
        nodes.set_edgecolor("gray")

    # Draw labels with better font and positioning
    nx.draw_networkx_labels(
        dag, pos, font_size=10, font_weight="bold", font_color="black"
    )

    # Add a legend to explain node colors and sizes
    legend_elements = []

    # Add legend for regular tasks
    if regular_tasks:
        legend_elements.append(
            mpatches.Patch(color=cmap(0.3), alpha=0.9, label="Regular Tasks")
        )

    # Add legend for sweep tasks
    if sweep_tasks:
        legend_elements.append(
            mpatches.Patch(color=cmap(0.7), alpha=0.9, label="Sweep Tasks")
        )

    # Add legend for node size
    legend_elements.append(
        mpatches.Patch(
            color="lightgray",
            alpha=0.0,
            label="Node size: number of connections",
        )
    )

    # Add the legend to the plot
    if legend_elements:
        plt.legend(
            handles=legend_elements,
            loc="upper right",
            frameon=True,
            framealpha=0.9,
            fontsize=10,
        )

    # Remove axis
    plt.axis("off")

    # Add a more descriptive title with better styling
    plt.title(
        "Workflow DAG Visualization", fontsize=18, fontweight="bold", pad=20
    )

    # Add padding around the graph
    plt.tight_layout(pad=2.0)

    if output_path:
        # Ensure directory exists
        os.makedirs(
            (
                os.path.dirname(output_path)
                if os.path.dirname(output_path)
                else "."
            ),
            exist_ok=True,
        )
        plt.savefig(output_path, bbox_inches="tight", dpi=300)
        plt.close()
        return output_path
    else:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            suffix=".png", delete=False
        ) as tmp_file:
            temp_path = tmp_file.name

        plt.savefig(temp_path, bbox_inches="tight", dpi=300)
        plt.close()

        print(f"DAG visualization saved to: {temp_path}")
        return temp_path
