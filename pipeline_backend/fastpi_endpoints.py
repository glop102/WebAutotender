from fastapi import APIRouter, status, Response
from fastapi.responses import HTMLResponse, JSONResponse
from .workflows import *
from .instances import *
from .variables import *
from .manager import PipelineManager

router = APIRouter()

# ===================================================================
# Workflows

@router.get("/workflows")
async def get_all_workflows():
    return [w.json_savable() for w in global_workflows]

@router.get("/workflows/{workflow_name}")
async def get_workflow(workflow_name: str):
    try:
        w = Workflow.get_by_name(workflow_name)
        return w.json_savable()
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

@router.put("/workflows/{workflow_name}")
async def edit_workflow(workflow_name: str, data: dict):
    pass

@router.post("/workflows/{workflow_name}/spawn_instance")
async def spawn_instance_of_workflow(workflow_name: str):
    pass

# ===================================================================
# Instances

@router.get("/instances")
async def get_all_instances():
    return [i.json_savable() for i in global_instances]

@router.get("/instances/{uuid}")
async def get_instance(uuid: str):
    try:
        i = Instance.get_by_uuid(uuid)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return i.json_savable()

@router.delete("/instances/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(uuid:str):
    try:
        i = Instance.get_by_uuid(uuid)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    global_instances.remove(i)

@router.put("/instances/{uuid}")
async def edit_instance(uuid:str,data:dict):
    pass
    


# ===================================================================
# Global Variables

@router.get("/global_variables")
async def get_all_global_vars():
    return global_variables

@router.get("/global_vars/{var_name}")
async def get_global_var(var_name:str):
    if var_name in global_variables:
        return global_variables[var_name].json_savable()
    return Response(status_code=status.HTTP_404_NOT_FOUND)

@router.delete("/global_vars/{var_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_global_var(var_name:str):
    if not var_name in global_variables:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    del global_variables[var_name]

@router.put("/global_vars/{var_name}")
async def create_global_var(var_name: str, data: dict):
    new_var = WorkVariable()
    try:
        new_var.json_loadable(data)
    except:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    
    if var_name in global_variables:
        global_variables[var_name] = new_var
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        global_variables[var_name] = new_var
        return Response(status_code=status.HTTP_201_CREATED)
