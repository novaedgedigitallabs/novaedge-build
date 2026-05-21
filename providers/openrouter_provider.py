import os
import time
import logging
from openai import OpenAI
from providers.base_provider import BaseProvider

logger = logging.getLogger("NovaEdgeBuild.Provider")

class OpenRouterProvider(BaseProvider):
    """
    OpenRouter API provider leveraging the OpenAI SDK compatibility layer.
    """
    
    def __init__(self, model: str = None, api_key: str = None):
        model = model or os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
        super().__init__(name="OpenRouter", model=model)
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.client = None
        
        if self.api_key and self.api_key != "your_openrouter_api_key_here":
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
                timeout=45.0  # 45 second timeout for robust cloud response
            )

    def validate(self) -> tuple[bool, str]:
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            return False, "OpenRouter API key is missing or is set to placeholder."
        if not self.client:
            return False, "OpenRouter client was not successfully initialized."
        return True, "OpenRouter configured and ready."

    def generate(self, system_prompt: str, user_prompt: str = None, messages: list = None, tools: list = None) -> tuple[str, list]:
        if not self.client:
            raise ValueError("OpenRouter client not initialized. Check API keys.")

        # Construct payload message list
        payload_messages = [{"role": "system", "content": system_prompt}]
        if messages:
            # If historical context is provided, append/extend it safely
            for msg in messages:
                if msg.get("role") != "system":  # We set custom system prompt separately
                    payload_messages.append(msg)
        if user_prompt is not None:
            payload_messages.append({"role": "user", "content": user_prompt})

        # Process tool mapping to OpenAI format
        openai_tools = None
        if tools:
            openai_tools = []
            for t in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"]
                    }
                })

        start_time = time.time()
        logger.info(f"[OpenRouter] Requesting inference for model {self.model}...")

        try:
            extra_headers = {
                "HTTP-Referer": "https://github.com/novaedge-digital-labs/novaedge-build",
                "X-Title": "NovaEdge Build OS"
            }
            
            # Request chat completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=payload_messages,
                tools=openai_tools,
                tool_choice="auto" if openai_tools else None,
                extra_headers=extra_headers
            )
            
            elapsed = time.time() - start_time
            logger.info(f"[OpenRouter] Request completed in {elapsed:.2f}s.")
            
            message = response.choices[0].message
            response_text = message.content
            
            tool_calls = []
            if message.tool_calls:
                import json
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "args": json.loads(tc.function.arguments)
                    })
                    
            return response_text, tool_calls

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[OpenRouter] Failure during inference after {elapsed:.2f}s: {e}")
            raise e
