from fastapi import APIRouter, status, Response
from fastapi.responses import HTMLResponse, JSONResponse
from .workflows import *
from .instances import *
from .variables import *
from .commands import *
from .manager import PipelineManager

router = APIRouter()

# ===================================================================
# Workflows
workflow_router = APIRouter(tags=["workflows"])

@workflow_router.get("/workflows")
async def get_all_workflows():
    return [w.json_savable() for w in global_workflows]

@workflow_router.get("/workflows/{workflow_name}")
async def get_workflow(workflow_name: str):
    try:
        w = Workflow.get_by_name(workflow_name)
        return w.json_savable()
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

@workflow_router.put("/workflows/{workflow_name}", status_code=status.HTTP_204_NO_CONTENT)
async def edit_workflow(workflow_name: str, data: dict):
    """Will create a new workflow or edit a workflow that already exists."""
    try:
        w_new = Workflow()
        w_new.json_loadable(data)
    except:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    try:
        w_orig = Workflow.get_by_name(workflow_name)
        global_workflows.remove(w_orig)
    except: pass
    global_workflows.append(w_new)

@workflow_router.post("/workflows/{workflow_name}/spawn_instance")
async def spawn_instance_of_workflow(workflow_name: str, setup_variables:dict):
    """Give a json list of WorkVariables to be used to setup the Instance that is spawned."""
    if not setup_variables:
        setup_variables = {}
    try:
        w = Workflow.get_by_name(workflow_name)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    try:
        for arg_name,arg_data in setup_variables.items():
            v = WorkVariable()
            v.json_loadable(arg_data)
            setup_variables[arg_name] = arg_data
    except:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    PipelineManager.notify_of_something_happening()
    return JSONResponse(w.spawn_instance(setup_variables).json_savable(), status_code=status.HTTP_201_CREATED)

@workflow_router.get("/workflows/{workflow_name}/instances")
async def get_workflow_instances(workflow_name: str):
    try:
        w = Workflow.get_by_name(workflow_name)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return [i.json_savable() for i in w.get_instances()]

@workflow_router.post("/workflows/{workflow_name}/pause", status_code=status.HTTP_204_NO_CONTENT)
async def pause_workflow(workflow_name: str):
    try:
        w = Workflow.get_by_name(workflow_name)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    w.state = RunStates.Paused

@workflow_router.post("/workflows/{workflow_name}/unpause", status_code=status.HTTP_204_NO_CONTENT)
async def unpause_workflow(workflow_name: str):
    try:
        w = Workflow.get_by_name(workflow_name)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    w.state = RunStates.Running

# ===================================================================
# Instances
instance_router = APIRouter(tags=["instances"])

@instance_router.get("/instances")
async def get_all_instances():
    return [i.json_savable() for i in global_instances]

@instance_router.get("/instances/orphans")
async def get_instance_orphans():
    workflow_names = [w.name for w in global_workflows]
    return [i.json_savable() for i in global_instances if not i.workflow_name in workflow_names]

@instance_router.get("/instances/{uuid}")
async def get_instance(uuid: str):
    try:
        i = Instance.get_by_uuid(uuid)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return i.json_savable()

@instance_router.delete("/instances/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(uuid:str):
    try:
        i = Instance.get_by_uuid(uuid)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    global_instances.remove(i)

@instance_router.put("/instances/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def edit_instance(uuid:str,data:dict):
    try:
        i_orig = Instance.get_by_uuid(uuid)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    try:
        i_new = Instance()
        i_new.json_loadable(data)
    except:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    global_instances.remove(i_orig)
    global_instances.append(i_new)
    PipelineManager.notify_of_something_happening()

@instance_router.post("/instances/{uuid}/pause", status_code=status.HTTP_204_NO_CONTENT)
async def pause_instance(uuid: str):
    try:
        i = Instance.get_by_uuid(uuid)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    i.state = RunStates.Paused

@instance_router.post("/instances/{uuid}/unpause", status_code=status.HTTP_204_NO_CONTENT)
async def unpause_instance(uuid: str):
    try:
        i = Instance.get_by_uuid(uuid)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    i.state = RunStates.Running
    PipelineManager.notify_of_something_happening()

@instance_router.post("/instances/{uuid}/run_now", status_code=status.HTTP_204_NO_CONTENT)
async def run_now_instance(uuid: str):
    try:
        i = Instance.get_by_uuid(uuid)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    i.state = RunStates.Running
    i.next_processing_time = datetime.now()
    PipelineManager.notify_of_something_happening()


# ===================================================================
# Global Variables
variable_router = APIRouter(tags=["variables"])

@variable_router.get("/global_variables")
async def get_all_global_vars():
    return global_variables

@variable_router.get("/global_vars/{var_name}")
async def get_global_var(var_name:str):
    if var_name in global_variables:
        return global_variables[var_name].json_savable()
    return Response(status_code=status.HTTP_404_NOT_FOUND)

@variable_router.delete("/global_vars/{var_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_global_var(var_name:str):
    if not var_name in global_variables:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    del global_variables[var_name]

@variable_router.put("/global_vars/{var_name}", status_code=status.HTTP_204_NO_CONTENT)
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

# ===================================================================
# Commands
command_router = APIRouter(tags=["commands"])

@command_router.get("/commands")
async def get_all_command_details():
    return Commands.json_savable_all_commands_with_args()

@command_router.get("/commands/{command_name}")
async def get_command_detail(command_name:str):
    try:
        return Commands.json_savable_command_information(command_name)
    except:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

# ===================================================================
# Variable Types

@variable_router.get("/variable_types")
async def get_all_variable_types():
    return [cls.__name__ for cls in WorkVariable.__subclasses__()]

router.include_router(workflow_router)
router.include_router(instance_router)
router.include_router(variable_router)
router.include_router(command_router)
