import os
import json
import urllib.request
import urllib.error
import logging

class EmbeddingManager:
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self.ollama_url = ollama_url
        self.model = model
        self.logger = logging.getLogger("EmbeddingManager")
        
        # Check if model exists, if not warn
        self.logger.info(f"Initialized EmbeddingManager with {self.model} at {self.ollama_url}")

    def generate_embedding(self, text: str) -> list[float]:
        """
        Calls Ollama to generate embeddings for a given text.
        """
        url = f"{self.ollama_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                return result.get("embedding", [])
        except urllib.error.URLError as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            # Return empty list or raise
            return []
