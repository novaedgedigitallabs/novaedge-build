import json
from tools.base_tool import BaseTool

class CreateAgentTool(BaseTool):
    @property
    def name(self) -> str:
        return "create_agent"

    @property
    def description(self) -> str:
        return "Spawns a new specialized agent profile dynamically on disk and registers it."

    @property
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "CamelCase name of the agent, e.g. ContentWriterAgent"},
                    "role": {"type": "string", "description": "Specific professional role description"},
                    "goals": {"type": "array", "items": {"type": "string"}, "description": "High level objectives"},
                    "responsibilities": {"type": "array", "items": {"type": "string"}, "description": "List of core responsibilities"},
                    "workflows": {"type": "array", "items": {"type": "string"}, "description": "Step-by-step procedure sequences"},
                    "tools": {"type": "array", "items": {"type": "string"}, "description": "Required technical tools"},
                    "rules": {"type": "array", "items": {"type": "string"}, "description": "Operational rules and constraints"}
                },
                "required": ["name", "role", "goals", "responsibilities", "workflows", "tools", "rules"]
            }
        }

    def execute(self, args: dict, context: dict = None) -> str:
        """
        Spawns a new agent.
        """
        if not context or "system" not in context:
            return json.dumps({"status": "error", "message": "No system context provided to create agent."})

        system = context["system"]
        try:
            # Call creator to write markdown file and register in registry
            filepath = system.creator.create_agent(
                name=args["name"],
                role=args["role"],
                goals=args["goals"],
                rules=args["rules"],
                responsibilities=args["responsibilities"],
                workflows=args["workflows"],
                tools=args["tools"]
            )
            # Log action to tool log
            if hasattr(system, 'log_tool_usage'):
                system.log_tool_usage(self.name, args, f"Successfully created agent: {args['name']} at {filepath}")
            
            # Log created agent to memory
            if hasattr(system, 'memory_manager'):
                system.memory_manager.record_agent_creation(args["name"], filepath, args["role"])

            return json.dumps({
                "status": "success",
                "filepath": filepath,
                "message": f"Agent '{args['name']}' created and registered successfully."
            })
        except Exception as e:
            if hasattr(system, 'log_tool_usage'):
                system.log_tool_usage(self.name, args, f"Error: {str(e)}")
            return json.dumps({"status": "error", "message": str(e)})
