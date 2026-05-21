import json
import logging
from tools.base_tool import BaseTool

logger = logging.getLogger("NovaEdgeBuild.Tool")

class DelegateTaskTool(BaseTool):
    @property
    def name(self) -> str:
        return "delegate_task"

    @property
    def description(self) -> str:
        return "Delegates a specific sub-task to a specialized agent and awaits their report."

    @property
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Name of target agent (e.g. 'seo_agent', 'social_media_agent')"},
                    "task_description": {"type": "string", "description": "Detailed prompt instruction for the agent"}
                },
                "required": ["agent_name", "task_description"]
            }
        }

    def execute(self, args: dict, context: dict = None) -> str:
        """
        Delegates the task to a sub-agent.
        """
        if not context or "system" not in context:
            return json.dumps({"status": "error", "message": "No system context provided to delegate task."})

        system = context["system"]
        agent_name = args["agent_name"]
        task_desc = args["task_description"]
        parent_task_id = context.get("parent_task_id")

        # Create sub-task in task manager
        sub_task_id = system.task_manager.create_task(
            description=task_desc,
            assigned_to=agent_name,
            dependencies=[parent_task_id] if parent_task_id else []
        )
        system.task_manager.update_task(sub_task_id, "in_progress")
        
        # Log to tool log
        if hasattr(system, 'log_tool_usage'):
            system.log_tool_usage(self.name, args, f"Delegating task {sub_task_id} to agent {agent_name}")

        # Run the sub-agent
        try:
            # Check if agent exists, if not, CEO should have checked list_agents or we raise error
            sub_agent = system.loader.load_agent(agent_name)
            result = system._execute_sub_agent(sub_agent, task_desc)
            system.task_manager.update_task(sub_task_id, "completed", result)
            
            # Log to agent execution log
            if hasattr(system, 'log_agent_action'):
                system.log_agent_action(agent_name, f"Task: {task_desc}\nResult: {result}")

            return json.dumps({
                "status": "success",
                "sub_task_id": sub_task_id,
                "result": result
            })
        except Exception as e:
            logger.error(f"Failed to execute sub-agent {agent_name}: {e}")
            system.task_manager.update_task(sub_task_id, "failed", str(e))
            return json.dumps({"status": "error", "message": f"Sub-agent execution failed: {str(e)}"})
