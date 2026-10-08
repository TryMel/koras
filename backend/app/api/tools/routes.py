from fastapi import APIRouter, HTTPException
from typing import List
from app.tools.registry import tool_registry, ToolContract

router = APIRouter(prefix="/tools", tags=["Tools Registry"])

@router.get("", response_model=List[ToolContract])
async def list_tools():
    return tool_registry.list_all()

@router.get("/{tool_id}", response_model=ToolContract)
async def get_tool(tool_id: str):
    tool = tool_registry.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Outil non trouvé.")
    return tool

@router.post("/{tool_id}/health")
async def check_tool_health(tool_id: str):
    tool = tool_registry.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Outil non trouvé.")
    if not tool.enabled:
        state = "disabled"
    elif tool.provider == "device":
        state = "device_required"
    else:
        state = "registered"
    return {"tool_id": tool_id, "status": state, "provider": tool.provider}
