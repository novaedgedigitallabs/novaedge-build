import os
import chromadb
from chromadb.config import Settings
import logging

class VectorMemory:
    def __init__(self, persist_directory: str = "memory/chroma_db"):
        self.logger = logging.getLogger("VectorMemory")
        self.persist_directory = os.path.abspath(persist_directory)
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        self.categories = [
            "business",
            "workflows",
            "technical",
            "agents",
            "user_preferences"
        ]
        
        self.collections = {}
        for cat in self.categories:
            self.collections[cat] = self.client.get_or_create_collection(
                name=cat,
                metadata={"description": f"{cat.capitalize()} Memory Collection"}
            )
            self.logger.info(f"Initialized ChromaDB collection: {cat}")

    def add_memory(self, category: str, memory_id: str, text: str, embedding: list[float], metadata: dict = None):
        """
        Adds a single memory to the specified category.
        """
        if category not in self.collections:
            self.logger.error(f"Category {category} not found.")
            return False
            
        metadata = metadata or {}
        # Ensure metadata values are strings, ints, floats or bools (ChromaDB requirement)
        safe_metadata = {k: str(v) if isinstance(v, (dict, list)) else v for k, v in metadata.items()}
        
        self.collections[category].upsert(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[safe_metadata]
        )
        return True

    def search_memory(self, category: str, query_embedding: list[float], n_results: int = 3, min_score: float = 0.5):
        """
        Searches a category for semantically similar memories.
        Note: ChromaDB distances are often cosine distance or L2. Lower is better.
        We'll treat distance as inverse to score.
        """
        if category not in self.collections:
            return []
            
        if self.collections[category].count() == 0:
            return []

        results = self.collections[category].query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        memories = []
        for i in range(len(results['ids'][0])):
            doc = results['documents'][0][i]
            meta = results['metadatas'][0][i]
            dist = results['distances'][0][i]
            
            # Convert distance to a similarity score 
            # (assuming default L2, closer to 0 is better. Let's do a simple inversion)
            score = max(0, 1.0 - (dist / 2.0))
            
            if score >= min_score:
                memories.append({
                    "id": results['ids'][0][i],
                    "content": doc,
                    "metadata": meta,
                    "score": score
                })
                
        return memories

    def delete_memory(self, category: str, memory_id: str):
        if category in self.collections:
            self.collections[category].delete(ids=[memory_id])
