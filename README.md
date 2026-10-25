1. Import the script into Neo4j:
   https://github.com/neo4j-graph-examples/movies/blob/main/scripts/movies.cypher

   Run the query in Neo4j.

2. Install the dependencies:
   `python -m pip install -r requirements.txt`

3. Configure the `.env` file:
   ```env
   NEO4J_URI=bolt://<instance>
   NEO4J_USERNAME=<username>
   NEO4J_PASSWORD=<password>
   NEO4J_DATABASE=<database>
   ```

4. Run the scripts in order:
   - `neo4j_export.py`: Export graph data to `data/edges.json` and `data/nodes.json`.
   - `build_rag.py`: Build RAG data from the Neo4j export, normalize it, and split it into chunks. Output: `data/documents.jsonl`.
   - `chroma_db.py`: Generate embeddings from `documents.jsonl` and store them in ChromaDB. Output: `chroma_db/`.
   - `rag_retrieval.py`: Run basic RAG retrieval.
   - `graph_retrieval.py`: Run basic graph retrieval.
