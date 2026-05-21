import json
from tools.base_tool import BaseTool

class RequestHumanApprovalTool(BaseTool):
    @property
    def name(self) -> str:
        return "request_human_approval"

    @property
    def description(self) -> str:
        return "Requests explicit confirmation from the human supervisor before proceeding with high impact steps."

    @property
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Detailed description of the risky action requiring approval"}
                },
                "required": ["reason"]
            }
        }

    def execute(self, args: dict, context: dict = None) -> str:
        """
        Requests human approval.
        Note: In the main loop, this is pre-approved/handled by the user approval prompt.
        This method logs and returns the approved status.
        """
        if not context or "system" not in context:
            return json.dumps({"status": "error", "message": "No system context provided."})

        system = context["system"]
        # Log tool usage to tool log
        if hasattr(system, 'log_tool_usage'):
            system.log_tool_usage(self.name, args, "Approved by human supervisor.")

        return json.dumps({"status": "approved", "message": "Approval granted by operator."})
