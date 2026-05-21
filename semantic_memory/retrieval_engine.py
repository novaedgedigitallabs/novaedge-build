import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any

from .embedding_manager import EmbeddingManager
from .vector_memory import VectorMemory

class RetrievalEngine:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.logger = logging.getLogger("RetrievalEngine")
        self.embed_manager = EmbeddingManager(ollama_url=ollama_url)
        self.vector_memory = VectorMemory()
        
        # Configuration
        self.similarity_threshold = 0.5
        self.max_context_items = 5

    def store_memory(self, category: str, content: str, metadata: dict = None) -> str:
        """
        Generates embedding and stores the memory.
        """
        mem_id = f"mem_{uuid.uuid4().hex[:8]}"
        embedding = self.embed_manager.generate_embedding(content)
        
        if not embedding:
            self.logger.warning(f"Skipping memory store for {mem_id}, failed to get embedding.")
            return None
            
        full_metadata = metadata or {}
        full_metadata["timestamp"] = datetime.now().isoformat()
        
        success = self.vector_memory.add_memory(
            category=category,
            memory_id=mem_id,
            text=content,
            embedding=embedding,
            metadata=full_metadata
        )
        
        if success:
            self.logger.info(f"Stored memory [{category}]: {mem_id}")
            return mem_id
        return None

    def retrieve_context(self, category: str, query: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Retrieves relevant memories based on query semantic similarity.
        """
        limit = limit or self.max_context_items
        embedding = self.embed_manager.generate_embedding(query)
        if not embedding:
            return []
            
        results = self.vector_memory.search_memory(
            category=category,
            query_embedding=embedding,
            n_results=limit,
            min_score=self.similarity_threshold
        )
        
        if results:
            self.logger.info(f"Retrieved {len(results)} context items from {category}")
            
        return results

    def cleanup_old_memories(self, category: str, days_old: int = 30):
        """
        Could be expanded to compress or remove stale memories.
        For now, stubbed for future expansion.
        """
        self.logger.info(f"Cleanup initialized for {category} older than {days_old} days.")
        pass

    def summarize_and_store_workflow(self, goal: str, tasks: list, result: str):
        """
        Automatic workflow summarization before storage.
        For a truly intelligent system, this might call a small LLM model 
        to summarize, but we'll use a heuristic template for local efficiency.
        """
        task_names = [t.get('name', 'Unknown') for t in tasks]
        summary = f"Workflow Goal: {goal}\nTasks Executed: {', '.join(task_names)}\nResult: {result}"
        
        self.store_memory(
            category="workflows",
            content=summary,
            metadata={"goal": goal, "type": "auto_summary"}
        )

