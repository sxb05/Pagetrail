from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from app.db.session import save_memory, search_memory
from app.services.rag import retrieve_documents

TAVILY_API_KEY = "TAVILY_API_KEY"

CURRENT_THID = "default"


def set_current_thid(thid: str):
    global CURRENT_THID
    CURRENT_THID = thid


@tool
def web_search(query: str, num_results: int = 5):
    """
    Perform a web search using Tavily and return the top results.
    """
    tavily = TavilySearch(api_key=TAVILY_API_KEY)
    results = tavily.search(query, num_results=num_results)
    return results


@tool
def save_memory_tool(content: str):
    """
    You are a helpful AI assistant with long-term memory.

    When the user explicitly tells you something useful to remember
    for future conversations, call save_memory_tool.

    Examples:
    - "My name is Subash" -> save it
    - "I am building a LangGraph RAG application" -> save it
    - "I prefer Python" -> save it

    Do not save temporary questions or one-time requests.
    """
    save_memory(CURRENT_THID, content)
    return f"Memory saved: {content}"


@tool
def search_memory_tool(query: str):
    """
    Search for memories in the database.
    """
    results = search_memory(CURRENT_THID, query)
    return results


@tool
def search_uploaded_documents(query: str, k: int = 5):
    """
    Search for uploaded documents in the vector store.
    """
    results = retrieve_documents(query, CURRENT_THID, k)
    return results


tools = [save_memory_tool, search_memory_tool, search_uploaded_documents, web_search]
