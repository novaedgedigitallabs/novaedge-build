import sys
from main import NovaEdgeBuildSystem

def test_full_flow():
    print("--- Starting NovaEdge Build Multi-Agent Simulation Test ---")
    system = NovaEdgeBuildSystem()
    
    # We set simulation mode to True explicitly for this test
    system.simulation_mode = True
    
    # Define a goal that involves SEO and Social Media coordination
    goal = "Create an SEO audit for the home page and draft a LinkedIn launch post."
    
    print(f"\n[Test] Sending Goal: '{goal}'")
    system.execute_user_goal(goal)
    
    print("\n--- Listing Executed Tasks in Task Manager ---")
    tasks = system.task_manager.list_tasks()
    for task in tasks:
        print(f"Task ID: {task['task_id']}")
        print(f"  Description: {task['description']}")
        print(f"  Assigned To: {task['assigned_to']}")
        print(f"  Status: {task['status']}")
        if task['result']:
            result_snippet = task['result'][:150].replace('\n', ' ')
            print(f"  Result Snippet: {result_snippet}...")
        print("-" * 30)

if __name__ == "__main__":
    test_full_flow()
