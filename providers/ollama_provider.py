import os
import time
import json
import logging
import re
import httpx
from providers.base_provider import BaseProvider

logger = logging.getLogger("NovaEdgeBuild.Provider")

# Default timeout for Ollama inference (seconds)
DEFAULT_OLLAMA_TIMEOUT = 600

# Models that support /no_think mode to skip reasoning traces
THINKING_MODELS = ["qwen3", "deepseek-r1"]

def normalize_model_name(name: str) -> str:
    """Helper function to normalize model names."""
    if not name or not isinstance(name, str):
        return ""
    name = name.strip().lower()
    if name.endswith(":latest"):
        return name[:-7]
    return name

class OllamaProvider(BaseProvider):
    """
    Ollama local LLM provider.
    Supports llama3, qwen2.5, qwen3.5, deepseek-r1, deepseek-coder, etc.
    """
    
    SUPPORTED_MODELS = ["llama3", "qwen2.5", "qwen3.5", "deepseek-r1", "deepseek-coder"]

    def __init__(self, model: str = None):
        model = model or os.getenv("OLLAMA_MODEL", "llama3")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", str(DEFAULT_OLLAMA_TIMEOUT)))
        self._is_thinking_model = any(
            normalize_model_name(model).startswith(prefix) for prefix in THINKING_MODELS
        )
        super().__init__(name="Ollama", model=model)
        
    def validate(self) -> tuple[bool, str]:
        try:
            import ollama
        except ImportError:
            return False, "Python library 'ollama' is not installed."
            
        try:
            # Check connection to Ollama server daemon
            response = ollama.list()
            logger.info(f"Raw Ollama response: {response}")
            
            models = []
            if isinstance(response, dict):
                models = response.get("models", [])
            elif hasattr(response, "models"):
                models = getattr(response, "models", [])
                
            downloaded_names = []
            for m in models:
                raw_name = ""
                # Defensive parsing for empty model entries, missing fields, or malformed tags
                if isinstance(m, dict):
                    raw_name = m.get("model") or m.get("name") or ""
                else:
                    raw_name = getattr(m, "model", None) or getattr(m, "name", "")
                
                if raw_name and isinstance(raw_name, str):
                    downloaded_names.append(raw_name.strip())

            downloaded_names = [name for name in downloaded_names if name]
            
            # Normalize target model
            target_norm = normalize_model_name(self.model)
            
            found = False
            for name in downloaded_names:
                name_norm = normalize_model_name(name)
                # Matches "qwen3.5" to "qwen3.5:latest" or "qwen3:8b" to "qwen3:8b", etc.
                if target_norm == name_norm or name_norm.startswith(target_norm + ":"):
                    found = True
                    break
                    
            if not found:
                return False, f"Ollama server is active, but target model '{self.model}' is missing. Pull it using 'ollama pull {self.model}'. Available local models: {downloaded_names}"
            
            return True, f"Ollama local provider active. Model '{self.model}' is ready."
        except Exception as e:
            return False, f"Ollama local daemon is unreachable/offline. Start the daemon first. Error: {e}"

    def _repair_and_validate_json(self, text: str) -> dict:
        """
        Attempts to extract, repair, and validate the JSON schema from the raw text.
        """
        # 1. Strip reasoning traces
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'Thinking Process:.*?(?=\{)', '', text, flags=re.DOTALL|re.IGNORECASE)
        text = re.sub(r'Thinking\.\.\..*?(?=\{)', '', text, flags=re.DOTALL|re.IGNORECASE)
        
        # 2. Extract JSON block
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            json_str = text[start_idx:end_idx+1]
        else:
            json_str = "{}"
            
        # 3. Attempt parse and basic repair
        parsed = {}
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            # Basic repair: add missing closing braces
            try:
                parsed = json.loads(json_str + "}")
            except json.JSONDecodeError:
                try:
                    parsed = json.loads(json_str + '"}')
                except json.JSONDecodeError:
                    parsed = {}
        
        # 4. Schema coercion and validation
        schema = {
            "thought": str(parsed.get("thought", "")),
            "action": str(parsed.get("action", "")).strip(),
            "arguments": parsed.get("arguments", {}),
            "final_response": str(parsed.get("final_response", ""))
        }
        
        if not isinstance(schema["arguments"], dict):
            schema["arguments"] = {}
            
        return schema

    def _get_effective_model(self, local_mode: bool) -> str:
        """
        Returns the effective model name. For thinking models in local mode,
        appends the :no_think tag to skip reasoning traces.
        """
        model = self.model
        if local_mode and self._is_thinking_model:
            # Append the no_think suffix to disable reasoning chain
            # This dramatically reduces latency for structured output
            base = normalize_model_name(model)
            model = base  # Use the clean base name
            logger.info(f"[Ollama] Thinking model detected. Will use /no_think for faster structured output.")
        return model

    def generate(self, system_prompt: str, user_prompt: str = None, messages: list = None, tools: list = None) -> tuple[str, list, dict]:
        import ollama
        
        # Check for local model mode
        local_mode = os.getenv("LOCAL_MODEL_MODE", "false").lower() == "true"
        
        # Build chat payload messages
        payload_messages = [{"role": "system", "content": system_prompt}]
        if messages:
            for msg in messages:
                if msg.get("role") != "system":
                    payload_messages.append(msg)
        if user_prompt is not None:
            payload_messages.append({"role": "user", "content": user_prompt})

        # For thinking models in local mode, inject /no_think into the user prompt
        if local_mode and self._is_thinking_model:
            # Append /no_think to the last user message to disable reasoning traces
            for i in range(len(payload_messages) - 1, -1, -1):
                if payload_messages[i]["role"] == "user":
                    payload_messages[i]["content"] += " /no_think"
                    break

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

        if local_mode:
            # Inject strict JSON orchestration instructions (Compact)
            structured_prompt = (
                "\n\n[OUTPUT FORMAT] Respond with valid JSON ONLY. No markdown or text outside JSON.\n"
                "SCHEMA: {\"thought\":\"brief reasoning\",\"action\":\"tool_name or empty\",\"arguments\":{},\"final_response\":\"message or empty\"}\n"
            )
            # If there are tools, mention them compactly
            if tools:
                tool_names = [t['name'] for t in tools]
                structured_prompt += "TOOLS: " + ", ".join(tool_names) + "\n"
                
            # Prepend to system prompt
            if payload_messages and payload_messages[0]["role"] == "system":
                payload_messages[0]["content"] = structured_prompt + payload_messages[0]["content"]
            else:
                payload_messages.insert(0, {"role": "system", "content": structured_prompt})

        start_time = time.time()
        effective_model = self._get_effective_model(local_mode)
        logger.info(f"[Ollama] Requesting inference for model '{effective_model}' (base: {self.model})...")
        logger.debug(f"[Ollama] Request sent with {len(payload_messages)} messages and {len(tools) if tools else 0} tools.")
        
        # Calculate system prompt size for logging
        sys_prompt_len = len(payload_messages[0]["content"]) if payload_messages else 0
        logger.info(f"[Ollama] System prompt size: {sys_prompt_len} chars")
        
        try:
            # Configure num_predict based on mode
            num_predict = 512 if local_mode else 2048
            
            options = {
                "num_predict": num_predict,
            }
            
            # For thinking models in local mode, explicitly disable thinking
            if local_mode and self._is_thinking_model:
                options["num_predict"] = 512  # Thinking models don't need long output for structured JSON
            
            chat_kwargs = {
                "model": effective_model,
                "messages": payload_messages,
                "stream": False,
                "options": options,
            }
            
            # Disable thinking at the API level for thinking models
            if local_mode and self._is_thinking_model:
                chat_kwargs["think"] = False
                logger.info("[Ollama] Thinking disabled via API option (think=False)")
            
            if local_mode:
                # Disable native tools in strict local mode to rely on structured JSON
                ollama_tools = None
                
            if ollama_tools:
                chat_kwargs["tools"] = ollama_tools
                
            logger.info(f"[Ollama] Provider call started. num_predict={num_predict}, timeout={self.timeout}s")
            
            if local_mode:
                chat_kwargs["stream"] = True
                
            # Timeout-safe retry system
            max_retries = 2
            for attempt in range(max_retries):
                response_text = ""
                response = None
                chunk_count = 0
                try:
                    try:
                        # Use httpx.Timeout with separate connect/read timeouts
                        # CPU inference can take 5-10 min for TTFT on large models
                        timeout_config = httpx.Timeout(
                            connect=30.0,      # 30s to establish connection
                            read=float(self.timeout),  # Full timeout for reading (TTFT + generation)
                            write=30.0,         # 30s to send request
                            pool=30.0           # 30s pool timeout
                        )
                        client = ollama.Client(
                            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                            timeout=timeout_config
                        )
                        logger.info(f"[Ollama] Attempt {attempt + 1}: Sending request (read_timeout={self.timeout}s)...")
                        api_response = client.chat(**chat_kwargs)
                    except TypeError:
                        api_response = ollama.chat(**chat_kwargs)
                        
                    if chat_kwargs.get("stream"):
                        last_chunk_time = time.time()
                        for chunk in api_response:
                            chunk_count += 1
                            if isinstance(chunk, dict):
                                chunk_text = chunk.get("message", {}).get("content", "")
                            else:
                                chunk_text = getattr(getattr(chunk, "message", None), "content", "") if hasattr(chunk, "message") else ""
                                
                            if chunk_text:
                                response_text += chunk_text
                                last_chunk_time = time.time()
                            
                            # Early-exit: try to parse valid JSON as soon as we see closing brace
                            if "}" in response_text:
                                parsed = self._repair_and_validate_json(response_text)
                                if parsed.get("action") or parsed.get("final_response"):
                                    logger.info(f"[Ollama] Stream early-exit at chunk {chunk_count}: Valid JSON found.")
                                    break
                            
                            # Guard against hanging stream (no new content for 30s)
                            if time.time() - last_chunk_time > 30:
                                logger.warning("[Ollama] Stream stalled for 30s. Breaking out.")
                                break
                                
                        response = {"message": {"content": response_text}}
                        logger.info(f"[Ollama] Stream completed. {chunk_count} chunks, {len(response_text)} chars.")
                    else:
                        response = api_response
                    break # Success, exit retry loop
                except (TimeoutError, httpx.TimeoutException, ConnectionError) as te:
                    if attempt < max_retries - 1:
                        logger.warning(f"[Ollama] Attempt {attempt + 1} timed out or failed. Retrying... ({te})")
                        time.sleep(2)
                        continue
                    raise te # Re-raise if all retries fail
            
            elapsed = time.time() - start_time
            logger.info(f"[Ollama] Provider response received. Request completed in {elapsed:.2f}s.")
            
            if os.getenv("DEBUG_MODE", "").lower() == "true":
                print(f"\n[DEBUG Ollama Raw Response]:\n{response}\n")
            
            if not response:
                logger.warning("[Ollama] Received empty response from provider.")
                return "", [], {"elapsed": elapsed, "error": "Empty response"}
                
            message = response.get("message") or {}
            response_text = message.get("content") or ""
            logger.info(f"[Ollama] Parsed content: {len(response_text)} chars.")
            
            tool_calls = []
            
            # Local Mode Structured Output Parsing
            if local_mode:
                parsed_json = self._repair_and_validate_json(response_text)
                action = parsed_json.get("action")
                args = parsed_json.get("arguments", {})
                
                if action and isinstance(action, str) and action.strip():
                    tool_calls.append({
                        "id": None,
                        "name": action.strip(),
                        "args": args if isinstance(args, dict) else {}
                    })
                
                # Update response text to just the final response or thought for logging
                response_text = parsed_json.get("final_response") or parsed_json.get("thought") or ""
                
                # In local mode, we might want to ensure the response text isn't completely empty if it failed
                if not response_text and not action:
                    response_text = "Task completed or unable to parse response."
            else:
                # Standard Native Tool Calling
                raw_tool_calls = message.get("tool_calls", [])
                if raw_tool_calls:
                    for tc in raw_tool_calls:
                        func = tc.get("function") or {}
                        args = func.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception as parse_e:
                                logger.warning(f"[Ollama] Failed to parse tool arguments for {func.get('name')}: {parse_e}")
                                args = {}
                        
                        if func.get("name"):
                            tool_calls.append({
                                "id": None,
                                "name": func.get("name"),
                                "args": args
                            })
                logger.info(f"[Ollama] Tool calls extracted: {len(tool_calls)} tools.")
            
            metadata = {
                "elapsed": elapsed,
                "model": self.model,
                "eval_count": response.get("eval_count", 0),
                "eval_duration": response.get("eval_duration", 0)
            }
            logger.info(f"[Ollama] Execution loop completed successfully.")
            return response_text, tool_calls, metadata

        except (TimeoutError, httpx.TimeoutException) as te:
            elapsed = time.time() - start_time
            logger.error(f"[Ollama] Inference timeout on model '{self.model}' after {elapsed:.2f}s: {te}")
            return "Error: Inference timeout.", [], {"elapsed": elapsed, "error": str(te)}
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[Ollama] Inference failure on model '{self.model}' after {elapsed:.2f}s: {e}")
            return f"Error: Inference failed: {str(e)}", [], {"elapsed": elapsed, "error": str(e)}
