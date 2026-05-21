import abc

class BaseProvider(abc.ABC):
    """
    Abstract Base class for AI model providers in the NovaEdge Build ecosystem.
    Every provider must implement inference execution and availability validation.
    """
    
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model

    @abc.abstractmethod
    def validate(self) -> tuple[bool, str]:
        """
        Validates if the provider is fully functional (e.g. API keys are set, 
        or local daemon is online, and requested model is available).
        
        Returns:
            (bool, str): (True, "Ready status description") or (False, "Failure reason description")
        """
        pass

    @abc.abstractmethod
    def generate(self, system_prompt: str, user_prompt: str = None, messages: list = None, tools: list = None) -> tuple[str, list, dict]:
        """
        Executes raw text generation and tool routing.
        
        Args:
            system_prompt: Guidelines and core behavior for the agent.
            user_prompt: Optional instructions for the specific task block.
            messages: Optional chat history to append/resume from.
            tools: Optional function calling schemas.
            
        Returns:
            (str, list, dict): (Response text content, list of requested tool calls, metadata)
        """
        pass
