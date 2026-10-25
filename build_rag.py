
import json
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path("data")
NODES_PATH = DATA_DIR / "nodes.json"
EDGES_PATH = DATA_DIR / "edges.json"
OUTPUT_PATH = DATA_DIR / "documents.jsonl"

# Chunking configuration:
# "edge" = each relationship becomes a chunk
# "group" = combine multiple relationships into a chunk
CHUNK_MODE = "edge"

# Applies only when CHUNK_MODE = "group"
CHUNK_SIZE = 8
CHUNK_OVERLAP = 2

RELATION_TEMPLATES = {
    "ACTED_IN": "{source} đóng phim {target}.",
    "DIRECTED": "{source} đạo diễn phim {target}.",
    "PRODUCED": "{source} sản xuất phim {target}.",
    "FOLLOWS": "{source} theo dõi {target}.",
    "REVIEWED": "{source} đánh giá phim {target}.",
    "WROTE": "{source} viết kịch bản phim {target}.",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_node_name(node):
    """Get a display name, preferring name over title."""
    props = node.get("properties", {})
    return props.get("name") or props.get("title") or node["id"]


def normalize_edge(edge, node_by_id):
    """Convert an edge into a normalized sentence."""
    source = node_by_id.get(edge["source"])
    target = node_by_id.get(edge["target"])

    if source is None or target is None:
        return None

    relation = edge["type"]
    template = RELATION_TEMPLATES.get(relation)

    # Do not generate a sentence for an undefined relationship type.
    if template is None:
        return None

    source_name = get_node_name(source)
    target_name = get_node_name(target)

    sentence = template.format(
        source=source_name,
        target=target_name,
    )

    if relation == "ACTED_IN":
        roles = edge.get("properties", {}).get("roles", [])
        if isinstance(roles, str):
            roles = [roles]
        roles = [role for role in roles if role]

        if roles:
            role_phrase = "vai diễn" if len(roles) == 1 else "các vai diễn"
            sentence = (
                f"{source_name} đóng phim {target_name} "
                f"với {role_phrase} {', '.join(roles)}."
            )

    return {
        "id": f"edge:{edge['id']}",
        "text": sentence,
        "source_type": relation,
        "source_id": edge["source"],
        "target_id": edge["target"],
        "edge_id": edge["id"],
    }


def make_chunks(documents, chunk_size=5, overlap=1):
    """
    Combine relationships into chunks.
    Only combine relationships of the same type to limit context mixing.
    """
    if chunk_size < 1:
        raise ValueError("chunk_size phải >= 1")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap phải >= 0 và nhỏ hơn chunk_size")

    groups = defaultdict(list)

    for doc in documents:
        groups[doc["source_type"]].append(doc)

    chunks = []
    step = chunk_size - overlap

    for relation, items in groups.items():
        for start in range(0, len(items), step):
            batch = items[start:start + chunk_size]

            if not batch:
                continue

            chunks.append({
                "id": (
                    f"chunk:{relation}:"
                    f"{start}:{batch[0]['id']}"
                ),
                "text": "\n".join(item["text"] for item in batch),
                "source_type": relation,
                "source_ids": [
                    item["source_id"] for item in batch
                ],
                "target_ids": [
                    item["target_id"] for item in batch
                ],
                "edge_ids": [
                    item["edge_id"] for item in batch
                ],
                "document_count": len(batch),
            })

            # Stop once the final item has been covered.
            if start + chunk_size >= len(items):
                break

    return chunks


def main():
    nodes = load_json(NODES_PATH)
    edges = load_json(EDGES_PATH)

    node_by_id = {node["id"]: node for node in nodes}

    normalized_documents = []
    skipped = defaultdict(int)

    for edge in edges:
        doc = normalize_edge(edge, node_by_id)

        if doc is None:
            skipped[edge["type"]] += 1
            continue

        normalized_documents.append(doc)

    if CHUNK_MODE == "edge":
        output_documents = normalized_documents
    elif CHUNK_MODE == "group":
        output_documents = make_chunks(
            normalized_documents,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP,
        )
    else:
        raise ValueError("CHUNK_MODE phải là 'edge' hoặc 'group'")

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for doc in output_documents:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"Nodes: {len(nodes)}")
    print(f"Edges: {len(edges)}")
    print(f"Normalized relationships: {len(normalized_documents)}")
    print(f"Output chunks: {len(output_documents)}")
    print(f"Chunk mode: {CHUNK_MODE}")

    if skipped:
        print("Skipped unsupported relationship types:", dict(skipped))

    print("\nSample output:")
    for doc in output_documents[:5]:
        print(json.dumps(doc, ensure_ascii=False))


if __name__ == "__main__":
    main()
