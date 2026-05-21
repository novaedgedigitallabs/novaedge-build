import json
from tools.base_tool import BaseTool

class SaveMemoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "save_memory"

    @property
    def description(self) -> str:
        return "Saves a key-value pair to short_term, long_term, or task_history memory."

    @property
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_type": {
                        "type": "string",
                        "enum": ["short_term", "long_term", "task_history"],
                        "description": "The target memory storage type."
                    },
                    "key": {"type": "string", "description": "A unique key/identifier for the memory entry."},
                    "value": {"type": "string", "description": "The data or content to store."}
                },
                "required": ["memory_type", "key", "value"]
            }
        }

    def execute(self, args: dict, context: dict = None) -> str:
        """
        Saves the memory key-value pair.
        """
        if not context or "system" not in context:
            return json.dumps({"status": "error", "message": "No system context provided to save memory."})

        system = context["system"]
        memory_type = args["memory_type"]
        key = args["key"]
        value = args["value"]

        try:
            if hasattr(system, 'memory_manager'):
                system.memory_manager.save_memory(memory_type, key, value)
                if hasattr(system, 'log_tool_usage'):
                    system.log_tool_usage(self.name, args, f"Saved to {memory_type} memory: {key}")
                return json.dumps({
                    "status": "success",
                    "message": f"Successfully stored '{key}' in {memory_type} memory."
                })
            else:
                return json.dumps({"status": "error", "message": "Memory manager not initialized in system."})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
