
import chromadb
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction,
)

client = chromadb.PersistentClient(path="./chroma_db")

embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

collection = client.get_collection(
    name="movies_rag_normalized",
    embedding_function=embedding_function,
)


def retrieve(query, top_k=5):
    result = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for i, doc_id in enumerate(result["ids"][0]):
        hits.append({
            "id": doc_id,
            "text": result["documents"][0][i],
            "metadata": result["metadatas"][0][i],
            "distance": result["distances"][0][i],
        })

    return hits


if __name__ == "__main__":
    while True:
        query = input("\nNhập câu hỏi (q để thoát): ").strip()

        if query.lower() == "q":
            break
        if not query:
            continue

        for rank, hit in enumerate(retrieve(query, top_k=5), start=1):
            print(f"\n#{rank} | distance={hit['distance']:.4f}")
            print(hit["text"])
            print("Metadata:", hit["metadata"])
