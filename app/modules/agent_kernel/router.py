from typing import Dict, Any, Optional
from .core.types import AgentType, Task, TaskResult
from .registry.registry import Registry
from ..semantic_kernel.agents.query_router_agent import QueryRouterAgent

class QueryRouter:
    """Router for handling queries using semantic kernel."""
    
    def __init__(self):
        self.registry = Registry()
        self.router_agent = QueryRouterAgent()
    
    async def route_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """Route a query to the appropriate agent."""
        try:
            # Use semantic kernel to analyze the query
            analysis_result = await self.router_agent.execute(query, context)
            
            if analysis_result.get("error"):
                return TaskResult(
                    task_id="",
                    agent_id="router",
                    status="error",
                    output={},
                    error=analysis_result["error"],
                    metadata=context
                )
            
            # Create a task for the selected agent
            task = Task(
                agent_type=AgentType(analysis_result["agent_type"]),
                input_data={"query": query},
                metadata=context
            )
            
            # Get the appropriate agent from the registry
            agent = self.registry.create_agent(task.agent_type)
            if not agent:
                return TaskResult(
                    task_id=task.task_id,
                    agent_id="router",
                    status="error",
                    output={},
                    error=f"No agent found for type: {task.agent_type}",
                    metadata=context
                )
            
            # Execute the task
            result = await agent.execute(task)
            return result
            
        except Exception as e:
            return TaskResult(
                task_id="",
                agent_id="router",
                status="error",
                output={},
                error=str(e),
                metadata=context
            )