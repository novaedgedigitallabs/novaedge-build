import os
import time
import logging
from providers.openrouter_provider import OpenRouterProvider
from providers.ollama_provider import OllamaProvider

logger = logging.getLogger("NovaEdgeBuild.Provider")

class ModelManager:
    """
    Central orchestrator for AI model provider selection, fallback logic, 
    and startup availability validation.
    """
    
    def __init__(self):
        self.provider_mode = os.getenv("MODEL_PROVIDER", "auto").strip().lower()
        self.openrouter = OpenRouterProvider()
        self.ollama = OllamaProvider()
        self.active_provider = None
        
        # Run startup configuration validation and print status
        self.startup_checks()

    def startup_checks(self):
        print("\n[Startup]")
        print("Checking providers...")
        logger.info("Running ModelManager startup checks...")

        or_valid, or_msg = self.openrouter.validate()
        ollama_valid, ollama_msg = self.ollama.validate()

        if self.provider_mode == "openrouter":
            logger.info("Forcing Cloud-Only Mode (OpenRouter).")
            if not or_valid:
                print(f"Error: OpenRouter is forced but failed validation: {or_msg}")
                logger.error(f"OpenRouter validation failed: {or_msg}")
            else:
                print(f"Using OpenRouter model: {self.openrouter.model}")
                self.active_provider = self.openrouter
                
        elif self.provider_mode == "ollama":
            logger.info("Forcing Local-Only Mode (Ollama).")
            if not ollama_valid:
                print(f"Error: Ollama is forced but failed validation: {ollama_msg}")
                logger.error(f"Ollama validation failed: {ollama_msg}")
            else:
                print(f"Using local model: {self.ollama.model}")
                self.active_provider = self.ollama
                
        else:  # "auto" or dynamic fallback mode
            if or_valid:
                print("OpenRouter key found.")
                print(f"Using OpenRouter model: {self.openrouter.model}")
                logger.info(f"OpenRouter active using model: {self.openrouter.model}")
                self.active_provider = self.openrouter
            else:
                print("No OpenRouter key found.")
                print("Falling back to Ollama.")
                logger.info("No valid OpenRouter configuration found. Defaulting to Ollama.")
                if ollama_valid:
                    print(f"Using local model: {self.ollama.model}")
                    logger.info(f"Ollama active using model: {self.ollama.model}")
                    self.active_provider = self.ollama
                else:
                    print(f"Warning: Local Ollama daemon validation failed: {ollama_msg}")
                    logger.warning(f"Ollama validation failed: {ollama_msg}")
                    # Keep active_provider None, we will retry/fallback dynamically during generation
                    self.active_provider = None
        print()

    def generate(self, system_prompt: str, user_prompt: str = None, messages: list = None, tools: list = None) -> tuple[str, list, dict]:
        """
        Routes the request to the active provider with automatic fallback logic.
        Uses cached validation from startup to avoid re-validating on every call.
        """
        # CASE 1: Forced OpenRouter Mode
        if self.provider_mode == "openrouter":
            print(f"[Provider] OpenRouter active")
            logger.info(f"Inference routed to OpenRouter: model={self.openrouter.model}")
            if self.active_provider is None:
                or_valid, or_msg = self.openrouter.validate()
                if not or_valid:
                    raise RuntimeError(f"OpenRouter provider validation failed: {or_msg}")
                self.active_provider = self.openrouter
            return self.openrouter.generate(system_prompt, user_prompt, messages, tools)

        # CASE 2: Forced Ollama Mode
        if self.provider_mode == "ollama":
            print(f"[Provider] Ollama active")
            logger.info(f"Inference routed to Ollama: model={self.ollama.model}")
            if self.active_provider is None:
                ollama_valid, ollama_msg = self.ollama.validate()
                if not ollama_valid:
                    raise RuntimeError(f"Ollama provider validation failed: {ollama_msg}")
                self.active_provider = self.ollama
            return self.ollama.generate(system_prompt, user_prompt, messages, tools)

        # CASE 3: Auto mode (automatic fallback logic)
        if self.active_provider == self.openrouter:
            try:
                print(f"[Provider] OpenRouter active")
                logger.info(f"Attempting inference via OpenRouter (model={self.openrouter.model})...")
                return self.openrouter.generate(system_prompt, user_prompt, messages, tools)
            except Exception as e:
                print(f"\n[Provider] OpenRouter execution failed: {e}")
                print(f"[Provider] Ollama fallback active")
                logger.warning(f"OpenRouter generation failed: {e}. Initiating Ollama fallback.")
                
                # Re-validate Ollama only on fallback
                ollama_valid, ollama_msg = self.ollama.validate()
                if not ollama_valid:
                    logger.critical(f"Ollama fallback target is unavailable: {ollama_msg}")
                    raise RuntimeError(f"OpenRouter failed, and local Ollama fallback is unavailable: {ollama_msg}") from e
                    
                self.active_provider = self.ollama
                logger.info(f"Executing fallback inference via local Ollama (model={self.ollama.model})...")
                return self.ollama.generate(system_prompt, user_prompt, messages, tools)
        else:
            # Active provider is Ollama (or None with auto mode)
            if self.active_provider is None:
                # Re-validate on first call if startup failed
                ollama_valid, ollama_msg = self.ollama.validate()
                if not ollama_valid:
                    raise RuntimeError(f"Ollama provider is unavailable: {ollama_msg}")
                self.active_provider = self.ollama
            print(f"[Provider] Ollama fallback active")
            logger.info(f"Routing directly to Ollama. model={self.ollama.model}")
            return self.ollama.generate(system_prompt, user_prompt, messages, tools)
