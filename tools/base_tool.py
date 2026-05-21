from abc import ABC, abstractmethod

class BaseTool(ABC):
    """
    Abstract base class for all tools in the NovaEdge Build Platform.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        The unique identifier/name for the tool.
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        A detailed description of what the tool does.
        """
        pass

    @property
    @abstractmethod
    def schema(self) -> dict:
        """
        The JSON schema defining the tool's parameters.
        """
        pass

    @abstractmethod
    def execute(self, args: dict, context: dict = None) -> str:
        """
        Executes the tool with the given arguments.
        Returns a string response containing execution output.
        """
        pass
