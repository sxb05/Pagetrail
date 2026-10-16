
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from app.db.session import save_memory, search_memory
from app.services.rag import retrieve_documents

TAVILY_API_KEY = "TAVILY_API_KEY"


def _get_request_identity(runtime: ToolRuntime) -> tuple[str, int]:
    configurable = runtime.config.get("configurable", {})

    thread_id = configurable.get("conversation_thread_id")
    user_id = configurable.get("user_id")

    if not isinstance(thread_id, str) or not thread_id:
        raise ValueError("Missing conversation context.")

    if isinstance(user_id, bool) or not isinstance(user_id, int):
        raise ValueError("Missing authenticated user context.")

    return thread_id, user_id


@tool
def web_search(query: str, num_results: int = 5):
    """Perform a web search using Tavily and return the top results."""
    tavily = TavilySearch(api_key=TAVILY_API_KEY)
    return tavily.search(query, num_results=num_results)


@tool
def save_memory_tool(content: str, runtime: ToolRuntime):
    """Save a useful memory for the authenticated user's conversation."""
    thread_id, user_id = _get_request_identity(runtime)
    save_memory(thread_id, user_id, content)
    return "Memory saved successfully."


@tool
def search_memory_tool(query: str, runtime: ToolRuntime):
    """Search memories belonging to the authenticated user's conversation."""
    thread_id, user_id = _get_request_identity(runtime)
    return search_memory(thread_id, user_id, query)


@tool
def search_uploaded_documents(
    query: str,
    runtime: ToolRuntime,
    k: int = 5,
):
    """Search uploaded documents belonging to the authenticated conversation."""
    thread_id, user_id = _get_request_identity(runtime)

    return retrieve_documents(
        query,
        thread_id,
        user_id,
        k=k,
    )


tools = [
    save_memory_tool,
    search_memory_tool,
    search_uploaded_documents,
    web_search,
]
