
import json
from pathlib import Path
from collections import deque

import networkx as nx

DATA = Path("data")

nodes = json.loads(
    (DATA / "nodes.json").read_text(encoding="utf-8")
)
edges = json.loads(
    (DATA / "edges.json").read_text(encoding="utf-8")
)

graph = nx.MultiDiGraph()

for node in nodes:
    graph.add_node(
        node["id"],
        labels=node.get("labels", []),
        properties=node.get("properties", {}),
    )

for edge in edges:
    graph.add_edge(
        edge["source"],
        edge["target"],
        key=edge["id"],
        id=edge["id"],
        type=edge["type"],
        properties=edge.get("properties", {}),
    )


def node_name(node_id):
    props = graph.nodes[node_id]["properties"]
    return str(props.get("name") or props.get("title") or node_id)


def find_entities(name):
    """Find entities by exact name without using an LLM."""
    query = name.casefold().strip()

    exact = [
        n for n in graph.nodes
        if node_name(n).casefold() == query
    ]
    if exact:
        return exact

    # Fall back to substring matching, which may return multiple entities.
    return [
        n for n in graph.nodes
        if query in node_name(n).casefold()
    ]


def retrieve_graph(entity_name, hops=1, relationship_types=None):
    seeds = find_entities(entity_name)

    if not seeds:
        return {
            "matched_entities": [],
            "triples": [],
        }

    allowed = (
        set(relationship_types)
        if relationship_types is not None
        else None
    )

    # Use BFS over undirected edges to find the neighborhood,
    # while preserving edge direction in the results.
    distance = {node: 0 for node in seeds}
    queue = deque(seeds)

    while queue:
        current = queue.popleft()

        if distance[current] >= hops:
            continue

        neighbors = set(graph.successors(current))
        neighbors.update(graph.predecessors(current))

        for neighbor in neighbors:
            if neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                queue.append(neighbor)

    visited = set(distance)
    triples = []

    for source, target, key, data in graph.edges(
        keys=True, data=True
    ):
        if source not in visited or target not in visited:
            continue

        # Include only edges within the visited neighborhood.
        if distance[source] > hops or distance[target] > hops:
            continue

        if allowed is not None and data["type"] not in allowed:
            continue

        triples.append({
            "source": node_name(source),
            "source_id": source,
            "relationship": data["type"],
            "target": node_name(target),
            "target_id": target,
            "edge_id": data["id"],
            "properties": data["properties"],
        })

    return {
        "matched_entities": [
            {"id": n, "name": node_name(n)} for n in seeds
        ],
        "triples": triples,
    }


if __name__ == "__main__":
    while True:
        name = input("\nTên phim/người (q để thoát): ").strip()
        if name.lower() == "q":
            break

        result = retrieve_graph(name, hops=1)

        print("\nThực thể tìm thấy:")
        for entity in result["matched_entities"]:
            print(entity)

        print("\nCác quan hệ:")
        for triple in result["triples"]:
            print(
                f"{triple['source']} "
                f"--[{triple['relationship']}]--> "
                f"{triple['target']}"
            )
            if triple["properties"]:
                print("  Properties:", triple["properties"])
