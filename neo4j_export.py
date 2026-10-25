
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

OUT_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True)


def to_jsonable(value):
    """Convert a Neo4j value into a JSON-serializable type."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    # Support date/time values and other special Neo4j types.
    if hasattr(value, "iso_format"):
        return value.iso_format()
    return str(value)


uri = os.environ["NEO4J_URI"]
auth = (
    os.environ["NEO4J_USERNAME"],
    os.environ["NEO4J_PASSWORD"],
)
database = os.getenv("NEO4J_DATABASE", "neo4j")

driver = GraphDatabase.driver(uri, auth=auth)

try:
    driver.verify_connectivity()

    with driver.session(database=database) as session:
        node_records = session.run("""
            MATCH (n)
            RETURN elementId(n) AS id,
                   labels(n) AS labels,
                   properties(n) AS properties
        """).data()

        edge_records = session.run("""
            MATCH (s)-[r]->(t)
            RETURN elementId(r) AS id,
                   elementId(s) AS source,
                   elementId(t) AS target,
                   type(r) AS type,
                   properties(r) AS properties
        """).data()

    nodes = [
        {
            "id": row["id"],
            "labels": row["labels"],
            "properties": to_jsonable(row["properties"]),
        }
        for row in node_records
    ]

    edges = [
        {
            "id": row["id"],
            "source": row["source"],
            "target": row["target"],
            "type": row["type"],
            "properties": to_jsonable(row["properties"]),
        }
        for row in edge_records
    ]

    (OUT_DIR / "nodes.json").write_text(
        json.dumps(nodes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "edges.json").write_text(
        json.dumps(edges, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Exported nodes: {len(nodes)}")
    print(f"Exported relationships: {len(edges)}")
    print(f"Output directory: {OUT_DIR.resolve()}")

finally:
    driver.close()
