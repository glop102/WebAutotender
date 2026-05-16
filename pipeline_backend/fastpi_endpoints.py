from fastapi import APIRouter, status, Response
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
from uuid import uuid4
from .workflows import Workflow, RunStates, ProcessingStep
from .instances import Instance
from .variables import WorkVariable
from .commands import Commands
from .manager import pipelineManager
from .event_callbacks import *

router = APIRouter()

# ===================================================================
# Workflows
workflow_router = APIRouter(tags=["workflows"])

@workflow_router.get("/workflows")
async def get_all_workflows():
    return {uuid: w.json_savable() for uuid,w in pipelineManager.ctx.workflows.items()}

@workflow_router.get("/workflows/{uuid}")
async def get_workflow(uuid: str):
    if not uuid in pipelineManager.ctx.workflows:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    w = pipelineManager.ctx.workflows[uuid]
    return w.json_savable()

@workflow_router.delete("/workflows/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(uuid: str):
    if not uuid in pipelineManager.ctx.workflows:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    del pipelineManager.ctx.workflows[uuid]
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.DeleteWorkflow,
        uuid
    )
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshWorkflows
    )

@workflow_router.put("/workflows/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def edit_workflow(uuid: str, data: dict):
    """Will create a new workflow or edit a workflow that already exists."""
    try:
        w_new = Workflow(pipelineManager.ctx)
        w_new.json_loadable(data)
    except:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    if uuid != w_new.uuid:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    pipelineManager.ctx.workflows[uuid] = w_new
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshWorkflow,
        uuid
    )
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshWorkflows
    )

@workflow_router.post("/workflows/{uuid}/spawn_instance")
async def spawn_instance_of_workflow(uuid: str, setup_variables:dict):
    """Give a json list of WorkVariables to be used to setup the Instance that is spawned."""
    if not setup_variables:
        setup_variables = {}
    if not uuid in pipelineManager.ctx.workflows:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    w = pipelineManager.ctx.workflows[uuid]
    try:
        setup_variables_cleaned = {}
        for arg_name,arg_data in setup_variables.items():
            v = WorkVariable()
            v.json_loadable(arg_data)
            setup_variables_cleaned[arg_name] = v
    except:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    new_instance = w.spawn_instance(setup_variables_cleaned)
    await pipelineManager.notify_of_something_happening()
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshInstance,
        new_instance.uuid
    )
    return JSONResponse(new_instance.json_savable(), status_code=status.HTTP_201_CREATED)

@workflow_router.get("/workflows/{uuid}/instances")
async def get_workflow_instances(uuid: str):
    if not uuid in pipelineManager.ctx.workflows:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    w = pipelineManager.ctx.workflows[uuid]
    return {i.uuid:i.json_savable() for i in w.get_instances()}

@workflow_router.post("/workflows/{uuid}/pause", status_code=status.HTTP_204_NO_CONTENT)
async def pause_workflow(uuid: str):
    if not uuid in pipelineManager.ctx.workflows:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    w = pipelineManager.ctx.workflows[uuid]
    w.state = RunStates.Paused
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshWorkflow,
        uuid
    )

@workflow_router.post("/workflows/{uuid}/unpause", status_code=status.HTTP_204_NO_CONTENT)
async def unpause_workflow(uuid: str):
    if not uuid in pipelineManager.ctx.workflows:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    w = pipelineManager.ctx.workflows[uuid]
    w.state = RunStates.Running
    await pipelineManager.notify_of_something_happening()
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshWorkflow,
        uuid
    )

@workflow_router.post("/workflows/{uuid}/toggle_pause", status_code=status.HTTP_204_NO_CONTENT)
async def toggle_pause_workflow(uuid: str):
    if not uuid in pipelineManager.ctx.workflows:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    w = pipelineManager.ctx.workflows[uuid]
    if w.state == RunStates.Running:
        w.state = RunStates.Paused
    else:
        w.state = RunStates.Running
        await pipelineManager.notify_of_something_happening()
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshWorkflow,
        uuid
    )

# ===================================================================
# Instances
instance_router = APIRouter(tags=["instances"])

@instance_router.get("/instances")
async def get_all_instances():
    return {i_name: pipelineManager.ctx.instances[i_name].json_savable() for i_name in pipelineManager.ctx.instances}

@instance_router.get("/instances/orphans")
async def get_instance_orphans():
    workflow_uuids = list(pipelineManager.ctx.workflows.keys())
    return { 
        uuid: i.json_savable() 
        for uuid,i in pipelineManager.ctx.instances.items()
        if not i.workflow_uuid in workflow_uuids
    }

@instance_router.get("/instances/{uuid}")
async def get_instance(uuid: str):
    if not uuid in pipelineManager.ctx.instances:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    i = pipelineManager.ctx.instances[uuid]
    return i.json_savable()

@instance_router.delete("/instances/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(uuid:str):
    if not uuid in pipelineManager.ctx.instances:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    del pipelineManager.ctx.instances[uuid]
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.DeleteInstance,
        uuid
    )

@instance_router.put("/instances/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def edit_instance(uuid:str,data:dict):
    try:
        i_new = Instance(pipelineManager.ctx)
        i_new.json_loadable(data)
    except:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    if uuid != i_new.uuid:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    pipelineManager.ctx.instances[uuid] = i_new
    await pipelineManager.notify_of_something_happening()
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshInstance,
        uuid
    )

@instance_router.post("/instances/{uuid}/pause", status_code=status.HTTP_204_NO_CONTENT)
async def pause_instance(uuid: str):
    if not uuid in pipelineManager.ctx.instances:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    i = pipelineManager.ctx.instances[uuid]
    i.state = RunStates.Paused
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshInstance,
        uuid
    )

@instance_router.post("/instances/{uuid}/unpause", status_code=status.HTTP_204_NO_CONTENT)
async def unpause_instance(uuid: str):
    if not uuid in pipelineManager.ctx.instances:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    i = pipelineManager.ctx.instances[uuid]
    i.state = RunStates.Running
    await pipelineManager.notify_of_something_happening()
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshInstance,
        uuid
    )

@instance_router.post("/instances/{uuid}/toggle_pause", status_code=status.HTTP_204_NO_CONTENT)
async def toggle_pause_instance(uuid: str):
    if not uuid in pipelineManager.ctx.instances:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    i = pipelineManager.ctx.instances[uuid]
    if i.state == RunStates.Running:
        i.state = RunStates.Paused
    else:
        i.state = RunStates.Running
        await pipelineManager.notify_of_something_happening()
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshInstance,
        uuid
    )

@instance_router.post("/instances/{uuid}/run_now", status_code=status.HTTP_204_NO_CONTENT)
async def run_now_instance(uuid: str):
    if not uuid in pipelineManager.ctx.instances:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    i = pipelineManager.ctx.instances[uuid]
    i.state = RunStates.Running
    i.next_processing_time = datetime.now()
    await pipelineManager.notify_of_something_happening()
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.RefreshInstance,
        uuid
    )


# ===================================================================
# Global Variables
variable_router = APIRouter(tags=["variables"])

@variable_router.get("/pipelineManager.ctx.variables")
async def get_all_global_vars():
    # {uuid: w.json_savable() for uuid, w in pipelineManager.ctx.workflows.items()}
    return {varname: gv.json_savable() for varname,gv in pipelineManager.ctx.variables.items()}

@variable_router.get("/pipelineManager.ctx.variables/{var_name}")
async def get_global_var(var_name:str):
    if var_name in pipelineManager.ctx.variables:
        return pipelineManager.ctx.variables[var_name].json_savable()
    return Response(status_code=status.HTTP_404_NOT_FOUND)

@variable_router.delete("/pipelineManager.ctx.variables/{var_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_global_var(var_name:str):
    if not var_name in pipelineManager.ctx.variables:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    del pipelineManager.ctx.variables[var_name]
    await eventsCallbackManager.signal_event(
        EventCallbacksManager.Events.DeleteGlobal,
        var_name
    )

@variable_router.put("/pipelineManager.ctx.variables/{var_name}", status_code=status.HTTP_204_NO_CONTENT)
async def create_global_var(var_name: str, data: dict):
    new_var = WorkVariable()
    try:
        new_var.json_loadable(data)
    except:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    
    if var_name in pipelineManager.ctx.variables:
        pipelineManager.ctx.variables[var_name] = new_var
        await eventsCallbackManager.signal_event(
            EventCallbacksManager.Events.RefreshGlobal,
            var_name
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        pipelineManager.ctx.variables[var_name] = new_var
        await eventsCallbackManager.signal_event(
            EventCallbacksManager.Events.RefreshGlobal,
            var_name
        )
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

# ===================================================================
# Random Utils
utils_router = APIRouter(tags=["utils"])

@utils_router.get("/gen_uuid")
async def get_gen_uuid():
    return str(uuid4())


router.include_router(workflow_router)
router.include_router(instance_router)
router.include_router(variable_router)
router.include_router(command_router)
router.include_router(utils_router)
