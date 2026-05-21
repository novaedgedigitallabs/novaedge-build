import os
import json
import uuid
from datetime import datetime

class TaskManager:
    """
    Manages task tracking, delegation, and state representation for the AI workforce.
    Saves task state to disk in memory/tasks.json to allow persistent multi-agent orchestration.
    """
    
    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = os.path.abspath(memory_dir)
        os.makedirs(self.memory_dir, exist_ok=True)
        
        self.db_path = os.path.join(self.memory_dir, "tasks.json")
        if not os.path.exists(self.db_path):
            self._save_tasks({})

    def create_task(self, description: str, assigned_to: str, dependencies: list = None) -> str:
        """
        Creates a new task, assigns it to an agent, and writes it to the task database.
        Returns the unique task ID.
        """
        task_id = str(uuid.uuid4())[:8] # Short unique ID for ease of readability
        tasks = self._load_tasks()
        
        tasks[task_id] = {
            "task_id": task_id,
            "description": description,
            "assigned_to": assigned_to,
            "status": "pending",  # pending, in_progress, completed, failed
            "dependencies": dependencies or [],
            "result": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self._save_tasks(tasks)
        print(f"[TaskManager] Task {task_id} created and assigned to {assigned_to}")
        return task_id

    def update_task(self, task_id: str, status: str, result: str = None) -> bool:
        """
        Updates the status and result of a task.
        """
        tasks = self._load_tasks()
        if task_id not in tasks:
            print(f"[TaskManager] Error: Task {task_id} not found.")
            return False
            
        tasks[task_id]["status"] = status
        tasks[task_id]["updated_at"] = datetime.now().isoformat()
        if result is not None:
            tasks[task_id]["result"] = result
            
        self._save_tasks(tasks)
        print(f"[TaskManager] Task {task_id} updated to status '{status}'")
        return True

    def get_task(self, task_id: str) -> dict:
        """
        Retrieves a single task's details.
        """
        tasks = self._load_tasks()
        return tasks.get(task_id)

    def list_tasks(self, filter_status: str = None, filter_agent: str = None) -> list:
        """
        Lists tasks, optionally filtering by status or assigned agent.
        """
        tasks = self._load_tasks()
        result = list(tasks.values())
        
        if filter_status:
            result = [t for t in result if t["status"] == filter_status]
        if filter_agent:
            result = [t for t in result if t["assigned_to"].lower() == filter_agent.lower()]
            
        return result

    def get_next_runnable_task(self) -> dict:
        """
        Finds a pending task whose dependencies are all completed.
        This provides a foundation for future autonomous multi-agent execution graphs.
        """
        tasks = self._load_tasks()
        for task in tasks.values():
            if task["status"] != "pending":
                continue
                
            # Check dependencies
            deps_met = True
            for dep_id in task["dependencies"]:
                dep_task = tasks.get(dep_id)
                if not dep_task or dep_task["status"] != "completed":
                    deps_met = False
                    break
                    
            if deps_met:
                return task
                
        return None

    def _load_tasks(self) -> dict:
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_tasks(self, tasks: dict):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4)

# Simple self-test validation when run directly
if __name__ == "__main__":
    tm = TaskManager(memory_dir="memory")
    t1 = tm.create_task("Analyze competitive landscaping", "SEOAgent")
    t2 = tm.create_task("Write promotional blog post", "SocialMediaAgent", dependencies=[t1])
    
    print("All tasks:")
    print(json.dumps(tm.list_tasks(), indent=2))
    
    print("\nNext runnable task:")
    print(tm.get_next_runnable_task()) # Should be t1 since it has no dependencies
    
    tm.update_task(t1, "completed", "Competitors are targeting 'AI agent builder'")
    
    print("\nNext runnable task after t1 completion:")
    print(tm.get_next_runnable_task()) # Should be t2 now that t1 is completed
