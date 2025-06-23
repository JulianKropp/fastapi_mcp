from fastapi import FastAPI, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from fastapi_mcp import FastApiMCP
from fastapi_mcp.types import HTTPRequestInfo
from typing import List, Dict, Optional
import uvicorn

API_KEY_PERMISSIONS = {
    "my-super-secret-token-1": ["/books"],
    "my-super-secret-token-2": ["/books/{book_id}"],
    "another-valid-key": ["*"],
}

app = FastAPI(
    title="Book Management System",
    description="A simple API to manage a collection of books.",
    version="0.1.0",
)

class Book(BaseModel):
    id: str
    title: str
    author: str

MOCK_BOOKS_DB: Dict[str, Book] = {
    "1": Book(id="1", title="The Hitchhiker's Guide to the Galaxy", author="Douglas Adams"),
    "2": Book(id="2", title="Dune", author="Frank Herbert"),
}

async def verify_permission(
    request: Request,
    x_mcp_key: str = Header(..., alias="X-Mcp-Key", description="The API key for authentication."),
):
    if x_mcp_key not in API_KEY_PERMISSIONS:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    allowed_paths = API_KEY_PERMISSIONS[x_mcp_key]
    if "*" in allowed_paths:
        return

    request_path_template = request.scope["route"].path

    if request_path_template not in allowed_paths:
        raise HTTPException(status_code=403, detail="API Key does not have permission for this endpoint")

@app.get("/books", response_model=List[Book], dependencies=[Depends(verify_permission)])
def list_books():
    return list(MOCK_BOOKS_DB.values())

@app.get("/books/{book_id}", response_model=Book, dependencies=[Depends(verify_permission)])
def read_book(book_id: str):
    if book_id not in MOCK_BOOKS_DB:
        raise HTTPException(status_code=404, detail=f"Book with ID '{book_id}' not found.")
    return MOCK_BOOKS_DB[book_id]

@app.get("/")
def read_root():
    return {"message": "Welcome to the Book Management System!"}

# Placeholder for the MCP server instance
mcp: Optional[FastApiMCP] = None

async def list_tools_for_key(http_request_info: Optional[HTTPRequestInfo]) -> List[str]:
    """Return the tool names available for the supplied API key."""
    if http_request_info is None:
        return []

    api_key = http_request_info.headers.get("x-mcp-key")
    if not api_key:
        return []

    allowed_paths = API_KEY_PERMISSIONS.get(api_key, [])
    if mcp is None:
        return []

    route_map = mcp.get_tool_route_map()

    if "*" in allowed_paths:
        return list(route_map.keys())

    return [name for name, info in route_map.items() if info["path"] in allowed_paths]

mcp = FastApiMCP(app, list_tools_callback=list_tools_for_key)
mcp.mount()

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_mcp.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["."],
        reload_includes=["*.py", "*.json", "*.yaml", "*.yml"],
        reload_excludes=["*.pyc", "*.pyo", "*.pyd", "*.pyi", "venv", "__pycache__", "venv/*", "venv/**"],
    )
