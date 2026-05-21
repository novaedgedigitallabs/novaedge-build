import os
import time
import logging
from providers.base_provider import BaseProvider

logger = logging.getLogger("NovaEdgeBuild.Provider")

class OllamaProvider(BaseProvider):
    """
    Ollama local LLM provider.
    Supports llama3, qwen2.5, deepseek-r1, deepseek-coder, etc.
    """
    
    SUPPORTED_MODELS = ["llama3", "qwen2.5", "deepseek-r1", "deepseek-coder"]

    def __init__(self, model: str = None):
        model = model or os.getenv("OLLAMA_MODEL", "llama3")
        super().__init__(name="Ollama", model=model)
        
    def validate(self) -> tuple[bool, str]:
        try:
            import ollama
        except ImportError:
            return False, "Python library 'ollama' is not installed."
            
        try:
            # Check connection to Ollama server daemon
            response = ollama.list()
            models = response.get("models", [])
            downloaded_names = [m.get("name", "").lower() for m in models]
            
            # Perform smart matching on model tags
            model_lower = self.model.lower()
            found = False
            for name in downloaded_names:
                # Matches "llama3" to "llama3:latest" or "llama3:8b", etc.
                if model_lower == name or model_lower + ":latest" == name or name.startswith(model_lower + ":"):
                    found = True
                    break
                    
            if not found:
                return False, f"Ollama server is active, but target model '{self.model}' is missing. Pull it using 'ollama pull {self.model}'. Available local models: {downloaded_names}"
            
            return True, f"Ollama local provider active. Model '{self.model}' is ready."
        except Exception as e:
            return False, f"Ollama local daemon is unreachable/offline. Start the daemon first. Error: {e}"

    def generate(self, system_prompt: str, user_prompt: str = None, messages: list = None, tools: list = None) -> tuple[str, list]:
        import ollama
        
        # Build chat payload messages
        payload_messages = [{"role": "system", "content": system_prompt}]
        if messages:
            for msg in messages:
                if msg.get("role") != "system":
                    payload_messages.append(msg)
        if user_prompt is not None:
            payload_messages.append({"role": "user", "content": user_prompt})

        # Process function calling schemas
        ollama_tools = None
        if tools:
            ollama_tools = []
            for t in tools:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"]
                    }
                })

        start_time = time.time()
        logger.info(f"[Ollama] Requesting inference for local model '{self.model}'...")
        
        try:
            # Execute chat completion
            # Ollama package supports 'tools' in versions >= 0.2.1
            chat_kwargs = {
                "model": self.model,
                "messages": payload_messages
            }
            if ollama_tools:
                chat_kwargs["tools"] = ollama_tools
                
            response = ollama.chat(**chat_kwargs)
            
            elapsed = time.time() - start_time
            logger.info(f"[Ollama] Request completed in {elapsed:.2f}s.")
            
            message = response.get("message", {})
            response_text = message.get("content", "")
            
            tool_calls = []
            raw_tool_calls = message.get("tool_calls", [])
            if raw_tool_calls:
                for tc in raw_tool_calls:
                    func = tc.get("function", {})
                    # Ensure arguments are parsed as dict if they are strings
                    args = func.get("arguments", {})
                    if isinstance(args, str):
                        import json
                        try:
                            args = json.loads(args)
                        except Exception:
                            pass
                    tool_calls.append({
                        "id": None,
                        "name": func.get("name"),
                        "args": args
                    })
                    
            return response_text, tool_calls

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[Ollama] Inference failure on model '{self.model}' after {elapsed:.2f}s: {e}")
            raise e
