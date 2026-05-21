import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import our modular AI architecture components
from agent_loader import AgentLoader
from agent_creator import AgentCreator
from task_manager import TaskManager
from model_manager import ModelManager

# Load environment variables
load_dotenv()

# Setup Logging
LOGS_DIR = os.path.abspath("logs")
os.makedirs(LOGS_DIR, exist_ok=True)
log_file = os.path.join(LOGS_DIR, f"execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("NovaEdgeBuild")

# ANSI Color Codes for Premium Console UI
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'

class NovaEdgeBuildSystem:
    """
    Main orchestrator for NovaEdge Build. Coordinates agents, tasks, memory,
    and handles interaction with the OpenAI API or fallback simulation.
    """
    
    def __init__(self):
        logger.info("Initializing NovaEdge Build Platform...")
        
        # Initialize directories
        for folder in ["memory", "workflows", "tools", "logs", "runtime", "configs"]:
            os.makedirs(folder, exist_ok=True)
            
        self.loader = AgentLoader(agents_dir="agents")
        self.creator = AgentCreator(agents_dir="agents", registry_path="configs/agents_registry.json")
        self.task_manager = TaskManager(memory_dir="memory")
        
        # Initialize Model Manager
        self.model_manager = ModelManager()
        self.simulation_mode = False
        if self.model_manager.active_provider is None:
            logger.warning("No valid model provider could be validated on startup. NovaEdge Build will run in SIMULATION MODE.")
            self.simulation_mode = True

        # Pre-register our starter agents in registry if not already done
        self._ensure_starter_agents_registered()

    def _ensure_starter_agents_registered(self):
        for agent in ["ceo", "seo_agent", "social_media_agent", "website_agent"]:
            try:
                profile = self.loader.load_agent(agent)
                self.creator.register_agent(profile["name"], f"{agent}.md", profile["role"])
            except Exception as e:
                logger.warning(f"Could not auto-register starter agent {agent}: {e}")

    def run_command_loop(self):
        """
        CLI Interface for running tasks and interacting with the CEO agent.
        """
        print(f"\n{Colors.HEADER}{Colors.BOLD}==================================================={Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}       NOVAEDGE BUILD - AI WORKFORCE PLATFORM      {Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}==================================================={Colors.ENDC}")
        print(f"Status: {'[Simulation Mode]' if self.simulation_mode else '[Live API Mode]'}")
        print("Type 'exit' or 'quit' to shut down.\n")

        while True:
            try:
                user_input = input(f"{Colors.BOLD}{Colors.CYAN}NovaEdgeBuild > {Colors.ENDC}").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    print(f"\n{Colors.GREEN}Shutting down NovaEdge Build. Goodbye!{Colors.ENDC}")
                    break
                
                self.execute_user_goal(user_input)
                
            except KeyboardInterrupt:
                print(f"\n{Colors.WARNING}Interrupted. Type 'exit' to quit.{Colors.ENDC}")
            except Exception as e:
                logger.exception(f"Error during execution: {e}")

    def execute_user_goal(self, goal: str):
        """
        Loads the CEO agent and kicks off the orchestration process.
        """
        logger.info(f"Processing goal: {goal}")
        
        # Load CEO Agent
        try:
            ceo = self.loader.load_agent("ceo")
        except FileNotFoundError:
            logger.error("CEO agent profile (ceo.md) not found. Re-check the agents directory.")
            return

        print(f"\n{Colors.BLUE}{Colors.BOLD}[System] Launching CEO Agent to orchestrate task...{Colors.ENDC}")
        
        # Create root task in manager
        root_task_id = self.task_manager.create_task(
            description=goal,
            assigned_to="CEO"
        )
        self.task_manager.update_task(root_task_id, "in_progress")

        # Define available tools schema for OpenAI function calling
        tools_schema = self._get_tools_schema()
        
        # Execution loop for agent conversation & tool execution
        messages = [
            {"role": "system", "content": ceo["system_prompt"]},
            {"role": "user", "content": f"User Goal: {goal}\nRoot Task ID: {root_task_id}"}
        ]
        
        step = 1
        max_steps = 10  # Prevent infinite loops
        
        while step <= max_steps:
            logger.info(f"CEO Agent execution step {step}...")
            
            if self.simulation_mode:
                response_text, tool_calls = self._simulate_ceo_response(goal, messages, step)
            else:
                response_text, tool_calls = self._call_openai(messages, tools_schema)

            # Log message to history
            if response_text:
                print(f"\n{Colors.GREEN}{Colors.BOLD}[CEO Agent]:{Colors.ENDC}\n{response_text}")
                messages.append({"role": "assistant", "content": response_text})
                
            if not tool_calls:
                # CEO completed the execution path or has no further actions
                self.task_manager.update_task(root_task_id, "completed", response_text)
                print(f"\n{Colors.GREEN}{Colors.BOLD}[System] CEO has concluded the workflow orchestration.{Colors.ENDC}\n")
                break
                
            # Process tool calls
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call.get("id", "sim_id")
                
                print(f"\n{Colors.WARNING}{Colors.BOLD}[CEO Action Requested]: {tool_name}{Colors.ENDC}")
                print(f"Arguments: {json.dumps(tool_args, indent=2)}")
                
                # Check for human in the loop for high risk actions
                if tool_name in ["create_agent", "execute_command", "request_human_approval"]:
                    approved = self._request_user_approval(tool_name, tool_args)
                    if not approved:
                        tool_result = "Action denied by human operator."
                        logger.warning(f"Action '{tool_name}' was rejected by user.")
                        messages.append({
                            "role": "function",
                            "name": tool_name,
                            "content": tool_result
                        })
                        continue

                # Run the actual tool
                tool_result = self.execute_tool(tool_name, tool_args, root_task_id)
                
                # Add tool response back to OpenAI message context
                messages.append({
                    "role": "function",
                    "name": tool_name,
                    "content": str(tool_result)
                })
                
            step += 1

        if step > max_steps:
            logger.warning("Reached maximum orchestration steps. Stopping to prevent run away loops.")
            self.task_manager.update_task(root_task_id, "failed", "Max steps exceeded.")

    def _call_openai(self, messages: list, tools: list) -> tuple:
        """
        Calls the model manager to get completion, supporting multiple providers and tool calling.
        """
        system_prompt = ""
        payload_messages = messages
        if messages and messages[0]["role"] == "system":
            system_prompt = messages[0]["content"]
            payload_messages = messages[1:]
            
        try:
            return self.model_manager.generate(
                system_prompt=system_prompt,
                messages=payload_messages,
                tools=tools
            )
        except Exception as e:
            logger.error(f"Model manager inference call failed: {e}")
            print(f"{Colors.FAIL}Error communicating with LLM provider. Switching this turn to simulation.{Colors.ENDC}")
            return "Error calling LLM provider. Switched to fallback simulation.", []

    def execute_tool(self, tool_name: str, args: dict, parent_task_id: str) -> str:
        """
        Routes tool calls to their respective python implementation handlers.
        """
        logger.info(f"Executing tool {tool_name} with args: {args}")
        
        if tool_name == "list_agents":
            agents = self.loader.list_available_agents()
            return json.dumps({"available_agents": agents})
            
        elif tool_name == "create_agent":
            try:
                filepath = self.creator.create_agent(
                    name=args["name"],
                    role=args["role"],
                    goals=args["goals"],
                    rules=args["rules"],
                    responsibilities=args["responsibilities"],
                    workflows=args["workflows"],
                    tools=args["tools"]
                )
                return json.dumps({"status": "success", "filepath": filepath, "message": f"Agent '{args['name']}' created."})
            except Exception as e:
                logger.error(f"Failed to create agent: {e}")
                return json.dumps({"status": "error", "message": str(e)})
                
        elif tool_name == "delegate_task":
            agent_name = args["agent_name"]
            task_desc = args["task_description"]
            
            # Create sub-task in task manager
            sub_task_id = self.task_manager.create_task(
                description=task_desc,
                assigned_to=agent_name,
                dependencies=[parent_task_id]
            )
            self.task_manager.update_task(sub_task_id, "in_progress")
            
            print(f"\n{Colors.BLUE}{Colors.BOLD}[System] Loading Sub-Agent: {agent_name}...{Colors.ENDC}")
            
            # Run sub-agent invocation
            try:
                sub_agent = self.loader.load_agent(agent_name)
                result = self._execute_sub_agent(sub_agent, task_desc)
                self.task_manager.update_task(sub_task_id, "completed", result)
                return json.dumps({"status": "success", "sub_task_id": sub_task_id, "result": result})
            except Exception as e:
                logger.error(f"Failed to execute sub-agent {agent_name}: {e}")
                self.task_manager.update_task(sub_task_id, "failed", str(e))
                return json.dumps({"status": "error", "message": f"Sub-agent execution failed: {str(e)}"})
                
        elif tool_name == "request_human_approval":
            # Already approved in pre-check, return status
            return json.dumps({"status": "approved", "message": "Approval granted by operator."})
            
        else:
            return json.dumps({"status": "error", "message": f"Unknown tool '{tool_name}'"})

    def _execute_sub_agent(self, agent_profile: dict, task_desc: str) -> str:
        """
        Executes a task using a loaded specialized agent profile.
        """
        print(f"{Colors.BLUE}[Sub-Agent {agent_profile['name']}] Processing: {task_desc}{Colors.ENDC}")
        
        if self.simulation_mode:
            # Generate offline mocked results matching the specific agent's domain
            return self._simulate_sub_agent_response(agent_profile["name"], task_desc)
            
        try:
            response_text, _ = self.model_manager.generate(
                system_prompt=agent_profile["system_prompt"],
                user_prompt=f"Execute this task and provide structured results: {task_desc}"
            )
            return response_text
        except Exception as e:
            logger.error(f"Sub-agent API call failed: {e}")
            return f"Error executing sub-agent: {e}"

    def _request_user_approval(self, action_name: str, args: dict) -> bool:
        """
        Prompts human-in-the-loop approval before executing dangerous operations.
        """
        print(f"\n{Colors.WARNING}{Colors.BOLD}⚠️  HUMAN APPROVAL REQUIRED FOR HIGH-RISK ACTION ⚠️{Colors.ENDC}")
        print(f"Action: {action_name}")
        print(f"Arguments: {json.dumps(args, indent=2)}")
        
        while True:
            response = input(f"{Colors.BOLD}{Colors.CYAN}Approve this action? (y/n): {Colors.ENDC}").strip().lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

    def _get_tools_schema(self) -> list:
        """
        Specifies the functional capability schema for the orchestrating agent.
        """
        return [
            {
                "name": "list_agents",
                "description": "Lists all available specialized agents in the system.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "create_agent",
                "description": "Spawns a new specialized agent profile dynamically on disk.",
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
            },
            {
                "name": "delegate_task",
                "description": "Delegates a specific sub-task to a specialized agent and awaits their report.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_name": {"type": "string", "description": "Name of target agent (e.g. 'seo_agent', 'social_media_agent')"},
                        "task_description": {"type": "string", "description": "Detailed prompt instruction for the agent"}
                    },
                    "required": ["agent_name", "task_description"]
                }
            },
            {
                "name": "request_human_approval",
                "description": "Requests explicit confirmation from the human supervisor before proceeding with high impact steps.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string", "description": "Detailed description of the risky action requiring approval"}
                    },
                    "required": ["reason"]
                }
            }
        ]

    # --- OFFLINE SIMULATION HANDLERS ---
    def _simulate_ceo_response(self, goal: str, messages: list, step: int) -> tuple:
        """
        Simulates structured CEO reasoning and tool calls for demonstration/testing.
        """
        if step == 1:
            text = "Analyzing the user's objective. I need to list existing workforce capabilities before mapping out task delegation."
            tool_calls = [{"name": "list_agents", "args": {}}]
            return text, tool_calls
            
        elif step == 2:
            # Let's inspect the user goal to simulate customized delegation
            lower_goal = goal.lower()
            if "seo" in lower_goal or "audit" in lower_goal or "keyword" in lower_goal:
                text = "Based on the request for search visibility, I will delegate the auditing and keyword strategy to the SEO agent."
                tool_calls = [{
                    "name": "delegate_task",
                    "args": {
                        "agent_name": "seo_agent",
                        "task_description": f"Perform analysis or audit for: '{goal}'"
                    }
                }]
            elif "social" in lower_goal or "post" in lower_goal or "campaign" in lower_goal or "linkedin" in lower_goal:
                text = "This goal falls under social engagement. I will delegate campaign drafting to our Social Media agent."
                tool_calls = [{
                    "name": "delegate_task",
                    "args": {
                        "agent_name": "social_media_agent",
                        "task_description": f"Draft campaign copy and layout for: '{goal}'"
                    }
                }]
            elif "website" in lower_goal or "page" in lower_goal or "html" in lower_goal:
                text = "This request involves frontend design and UI structure. I will delegate layout creation to the Website agent."
                tool_calls = [{
                    "name": "delegate_task",
                    "args": {
                        "agent_name": "website_agent",
                        "task_description": f"Create web layouts and components for: '{goal}'"
                    }
                }]
            else:
                # If it's a generic SaaS task, let's create a custom agent!
                text = "To address this software development request effectively, we require a specialized backend/database designer. I will spawn a new agent."
                tool_calls = [{
                    "name": "create_agent",
                    "args": {
                        "name": "DatabaseSpecialist",
                        "role": "Database Architect and Schema Design Specialist",
                        "goals": ["Create optimized relational and non-relational database models", "Formulate migration strategies"],
                        "responsibilities": ["Draft SQL schemas", "Review index structures for performance"],
                        "workflows": ["Analyze data requirements", "Produce clean database diagrams and schema code"],
                        "tools": ["generate_schema", "optimize_indexes"],
                        "rules": ["Follow clean schema conventions", "Ensure primary and foreign keys are explicitly named"]
                    }
                }]
            return text, tool_calls
            
        elif step == 3:
            # After delegation, return summary and finish
            text = f"I have collected the outputs and completed the orchestration process for '{goal}'. The tasks have been successfully processed, logged to disk, and verified."
            return text, []
            
        return "Task complete.", []

    def _simulate_sub_agent_response(self, agent_name: str, task_desc: str) -> str:
        """
        Mocked answers simulating specialist agent outputs.
        """
        if "seo_agent" in agent_name.lower():
            return """### SEO Audit & Recommendations Report
**Target Task:** Analysis of search visibility requirements.

1. **Competitor Keyword Targets:**
   - Identified gaps in search terms relating to 'No-Code AI platforms' and 'autonomous workforce orchestration'.
   - Recommended focus primary keyword: `autonomous AI workforce platform` (Search Volume: 5,400/mo, Difficulty: Medium).
   
2. **On-Page Recommendations:**
   - **H1 Header:** "Orchestrate Your Operations with NovaEdge Build"
   - **Meta Description:** "Deploy specialized, markdown-based AI agents to manage, scale, and automate your software company workflows dynamically."
   
3. **Structured Data:**
   - Recommend injecting JSON-LD SoftwareApplication schema to surface rich search snippets in Google.
"""
        elif "social_media_agent" in agent_name.lower():
            return """### Social Media Campaign Draft
**Platform: LinkedIn**
**Hook:** Stop managing bots. Start leading an autonomous workforce. 🤖💼

NovaEdge Digital Labs is proud to present **NovaEdge Build**—the operational OS designed for multi-agent coordination.
- Dynamic Agent Spawning 🚀
- Markdown-Based Profile Configuration 📄
- Human-in-the-Loop Safeguards 🛑

Read the architectural blueprint below and share your thoughts!
#AIAgents #SoftwareEngineering #StartupTools #NovaEdgeBuild

---

**Platform: Twitter/X (Thread Proposal)**
1/6 Meet NovaEdge Build: the autonomous workforce engine that doesn't just chat—it operates. Here's how we're scaling agent coordination at NovaEdge Digital Labs. 👇
2/6 Traditional agents operate in silos. NovaEdge Build introduces a hierarchical CEO Agent that dynamically assigns sub-tasks and reviews outputs.
3/6 Profiles are written in clean, human-readable Markdown. Want to spawn a database optimizer? The CEO writes the markdown and loads it instantly.
4/6 Safeties matter. Any file write or code execution requires human-in-the-loop permission via CLI/Dashboard. Safety first.
5/6 Powered by task dependency maps (DAGs), agents communicate and pass logs to memory files.
6/6 Want to learn more? Check out our documentation and build your own autonomous workforce. [Link]
"""
        elif "website_agent" in agent_name.lower():
            return """### Frontend Interface & Styling Blueprint
**Glassmorphism-Theme Component Layout:**

```html
<section class="nova-hero-container">
  <div class="glass-panel">
    <span class="badge">NovaEdge Build</span>
    <h1>Deploy an Autonomous AI Workforce</h1>
    <p>Coordinate, spin up, and manage specialized agents dynamically in one unified company operating system.</p>
    <div class="cta-group">
      <button class="btn-primary" id="btnLaunch">Launch Console</button>
      <button class="btn-secondary" id="btnDocs">Read Blueprint</button>
    </div>
  </div>
</section>
```

```css
:root {
  --primary-glow: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
  --panel-bg: rgba(255, 255, 255, 0.03);
  --border-color: rgba(255, 255, 255, 0.08);
  --text-primary: #f8fafc;
}

.nova-hero-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
  background: radial-gradient(circle at center, #0f172a 0%, #020617 100%);
}

.glass-panel {
  padding: 3rem;
  border-radius: 16px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-panel:hover {
  transform: translateY(-5px);
  border-color: rgba(0, 242, 254, 0.3);
}
```
"""
        else:
            return f"Default mock response for newly created specialist: {agent_name}. Output for task: {task_desc} generated successfully."

# Start-up sequence
if __name__ == "__main__":
    system = NovaEdgeBuildSystem()
    system.run_command_loop()
