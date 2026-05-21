from main import NovaEdgeBuildSystem
import sys

def test_real():
    print("--- Starting NovaEdge Build Real Execution ---")
    system = NovaEdgeBuildSystem()
    system.simulation_mode = False # Force real execution
    goal = "Create a brief SEO audit strategy"
    system.execute_user_goal(goal)

if __name__ == "__main__":
    test_real()
