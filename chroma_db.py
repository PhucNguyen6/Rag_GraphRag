
import json
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction,
)

INPUT_PATH = Path("data/documents.jsonl")
DB_PATH = "./chroma_db"
COLLECTION_NAME = "movies_rag_normalized"

embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path=DB_PATH)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_function,
    metadata={"hnsw:space": "cosine"},
)

documents = []
with INPUT_PATH.open("r", encoding="utf-8") as f:
    for line in f:
        documents.append(json.loads(line))

batch_size = 100

for start in range(0, len(documents), batch_size):
    batch = documents[start:start + batch_size]

    ids = [item["id"] for item in batch]
    texts = [item["text"] for item in batch]

    metadatas = []
    for item in batch:
        metadata = {
            "source_type": item["source_type"],
            "document_count": item.get("document_count", 1),
        }

        if "edge_id" in item:
            metadata["edge_id"] = item["edge_id"]
            metadata["source_id"] = item["source_id"]
            metadata["target_id"] = item["target_id"]

        if "edge_ids" in item:
            metadata["edge_ids"] = json.dumps(item["edge_ids"])
            metadata["source_ids"] = json.dumps(item["source_ids"])
            metadata["target_ids"] = json.dumps(item["target_ids"])

        metadatas.append(metadata)

    collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
    )

print("Collection:", COLLECTION_NAME)
print("Documents:", collection.count())
