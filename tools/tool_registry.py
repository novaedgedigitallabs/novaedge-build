import logging
from typing import Dict, List, Optional
from tools.base_tool import BaseTool
from tools.list_agents_tool import ListAgentsTool
from tools.create_agent_tool import CreateAgentTool
from tools.delegate_task_tool import DelegateTaskTool
from tools.save_memory_tool import SaveMemoryTool
from tools.request_human_approval_tool import RequestHumanApprovalTool

logger = logging.getLogger("NovaEdgeBuild.Tool")

class ToolRegistry:
    """
    Registry for managing available autonomous tools. Handles discovery, schemas,
    and routing execution calls.
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """
        Instantiates and registers default platform tools.
        """
        self.register_tool(ListAgentsTool())
        self.register_tool(CreateAgentTool())
        self.register_tool(DelegateTaskTool())
        self.register_tool(SaveMemoryTool())
        self.register_tool(RequestHumanApprovalTool())

    def register_tool(self, tool: BaseTool):
        """
        Registers a new tool instance in the registry.
        """
        name = tool.name
        if name in self._tools:
            logger.warning(f"Overwriting tool registration for '{name}'")
        self._tools[name] = tool
        logger.info(f"Registered tool: {name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Retrieves a tool by name.
        """
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """
        Lists all registered tool instances.
        """
        return list(self._tools.values())

    def get_all_schemas(self) -> List[dict]:
        """
        Compiles the schemas of all registered tools dynamically.
        """
        return [tool.schema for tool in self._tools.values()]
