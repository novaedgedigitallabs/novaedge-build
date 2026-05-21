import os
import json
from datetime import datetime

class MemoryManager:
    """
    Manages structured short-term, long-term, and task-history directories.
    Provides utility methods to store previous tasks, created agents, completed
    workflows, and tool usage history.
    """
    
    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = os.path.abspath(memory_dir)
        self.short_term_dir = os.path.join(self.memory_dir, "short_term")
        self.long_term_dir = os.path.join(self.memory_dir, "long_term")
        self.task_history_dir = os.path.join(self.memory_dir, "task_history")
        
        # Ensure directories exist
        for d in [self.short_term_dir, self.long_term_dir, self.task_history_dir]:
            os.makedirs(d, exist_ok=True)

    def save_memory(self, memory_type: str, key: str, value: str):
        """
        Saves key-value data to the designated memory subfolder.
        """
        target_dir = {
            "short_term": self.short_term_dir,
            "long_term": self.long_term_dir,
            "task_history": self.task_history_dir
        }.get(memory_type, self.short_term_dir)
        
        file_path = os.path.join(target_dir, f"{key}.json")
        data = {
            "key": key,
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def read_memory(self, memory_type: str, key: str) -> dict:
        """
        Reads data from the designated memory subfolder.
        """
        target_dir = {
            "short_term": self.short_term_dir,
            "long_term": self.long_term_dir,
            "task_history": self.task_history_dir
        }.get(memory_type, self.short_term_dir)
        
        file_path = os.path.join(target_dir, f"{key}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def list_memories(self, memory_type: str) -> list:
        """
        Lists key names stored in the memory subfolder.
        """
        target_dir = {
            "short_term": self.short_term_dir,
            "long_term": self.long_term_dir,
            "task_history": self.task_history_dir
        }.get(memory_type, self.short_term_dir)
        
        if not os.path.exists(target_dir):
            return []
        return [f.replace(".json", "") for f in os.listdir(target_dir) if f.endswith(".json")]

    def record_agent_creation(self, name: str, filepath: str, role: str):
        """
        Persists a registry of newly spawned agents in long-term memory.
        """
        agents_file = os.path.join(self.long_term_dir, "created_agents.json")
        data = []
        if os.path.exists(agents_file):
            try:
                with open(agents_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []
        data.append({
            "name": name,
            "filepath": filepath,
            "role": role,
            "timestamp": datetime.now().isoformat()
        })
        with open(agents_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def record_workflow_completion(self, goal: str, root_task_id: str, status: str, summary: str):
        """
        Appends completed workflows to long-term memory.
        """
        workflows_file = os.path.join(self.long_term_dir, "completed_workflows.json")
        data = []
        if os.path.exists(workflows_file):
            try:
                with open(workflows_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []
        data.append({
            "goal": goal,
            "root_task_id": root_task_id,
            "status": status,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        })
        with open(workflows_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def record_tool_call(self, tool_name: str, args: dict, result: str):
        """
        Logs tool usage history in short-term memory.
        """
        tool_file = os.path.join(self.short_term_dir, "tool_usage_history.json")
        data = []
        if os.path.exists(tool_file):
            try:
                with open(tool_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []
        data.append({
            "tool_name": tool_name,
            "args": args,
            "result_snippet": result[:200] if result else "",
            "timestamp": datetime.now().isoformat()
        })
        # Keep capped at 100 entries
        if len(data) > 100:
            data = data[-100:]
        with open(tool_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
