import json
import mimetypes
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

import pipeline_backend
from pipeline_backend.commands import Commands
from pipeline_backend.event_callbacks import (
    EventCallbacksManager,
    ServerSideSignalsQueue,
    eventsCallbackManager,
)
from pipeline_backend.instances import Instance, global_instances
from pipeline_backend.manager import pipelineManager
from pipeline_backend.variables import WorkVariable, global_variables
from pipeline_backend.workflows import RunStates, Workflow, global_workflows, ProcessingStep

# ---------------------------------------------------------------------------
# Router + templates
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/ui")
_template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_template_dir))

# ---------------------------------------------------------------------------
# Jinja2 globals / filters
# ---------------------------------------------------------------------------

def _enumerate_filter(iterable):
    return list(enumerate(iterable))

templates.env.filters["enumerate"] = _enumerate_filter
templates.env.filters["tojson"] = json.dumps

# ---------------------------------------------------------------------------
# Draft state
# ---------------------------------------------------------------------------

workflow_drafts: dict[str, Workflow] = {}
globals_draft: dict[str, WorkVariable] | None = None


def _get_or_create_workflow_draft(uuid: str) -> Workflow | None:
    if uuid not in global_workflows:
        return None
    if uuid not in workflow_drafts:
        workflow_drafts[uuid] = deepcopy(global_workflows[uuid])
    return workflow_drafts[uuid]


def _get_or_create_globals_draft() -> dict[str, WorkVariable]:
    global globals_draft
    if globals_draft is None:
        globals_draft = deepcopy(global_variables)
    return globals_draft


def _is_draft_dirty(uuid: str) -> bool:
    if uuid not in workflow_drafts or uuid not in global_workflows:
        return False
    saved = global_workflows[uuid]
    draft = workflow_drafts[uuid]
    return saved.json_savable() != draft.json_savable()


def _is_globals_draft_dirty() -> bool:
    if globals_draft is None:
        return False
    return {k: v.json_savable() for k, v in globals_draft.items()} != \
           {k: v.json_savable() for k, v in global_variables.items()}


# ---------------------------------------------------------------------------
# Helper: list of all WorkVariable type names
# ---------------------------------------------------------------------------

def _var_type_names() -> list[str]:
    return [cls.__name__ for cls in WorkVariable.__subclasses__()]


# ---------------------------------------------------------------------------
# Helper: command arg info for templates
# command_args: dict[cmd_name -> list[(arg_name, type_str_or_list)]]
# ---------------------------------------------------------------------------

def _command_args_for_template() -> dict:
    result = {}
    for name in Commands.commands:
        args = Commands.get_command_input_variables(name)
        rendered = []
        for arg_name, arg_types in args:
            if isinstance(arg_types, tuple):
                rendered.append((arg_name, [t.__name__ for t in arg_types]))
            else:
                rendered.append((arg_name, arg_types.__name__))
        result[name] = rendered
    return result


# ---------------------------------------------------------------------------
# Helper: build common design-tab context
# ---------------------------------------------------------------------------

def _design_context(workflow_uuid: str, draft: Workflow) -> dict:
    return {
        "workflow": draft,
        "workflow_uuid": workflow_uuid,
        "var_types": _var_type_names(),
        "command_names": list(Commands.commands.keys()),
        "command_args": _command_args_for_template(),
        "dirty": _is_draft_dirty(workflow_uuid),
        "active_tab": "design",
    }


def _instances_context(workflow: Workflow) -> dict:
    insts = [i for i in global_instances.values() if i.workflow_uuid == workflow.uuid]
    return {
        "workflow": workflow,
        "workflow_uuid": workflow.uuid,
        "instances": insts,
        "var_types": _var_type_names(),
        "active_tab": "instances",
    }


# ---------------------------------------------------------------------------
# Helper: resolve a JSON path into (parent_container, key) within a variable
# path is a list of str/int keys navigating into VariableList or Dictionary
# ---------------------------------------------------------------------------

def _resolve_var_path(var: WorkVariable, path: list):
    """Walk path into a nested WorkVariable container.
    Returns (container_workvar, final_key) where container_workvar.value[final_key] is the target.
    If path is empty, returns (None, None) meaning the var itself is the target.
    """
    node = var
    for key in path[:-1]:
        if isinstance(key, int):
            node = node.value[key]
        else:
            node = node.value[key]
    if not path:
        return None, None
    last = path[-1]
    return node, last


# ---------------------------------------------------------------------------
# Helper: navigate draft variables by section
# ---------------------------------------------------------------------------

def _section_vars(draft: Workflow, section: str) -> dict[str, WorkVariable]:
    if section == "constants":
        return draft.constants
    if section == "setup_variables":
        return draft.setup_variables
    raise ValueError(f"Unknown section: {section}")


# ---------------------------------------------------------------------------
# Helper: toast OOB fragment
# ---------------------------------------------------------------------------

def _toast_oob(message: str) -> str:
    return (
        f'<div id="toast" hx-swap-oob="outerHTML:#toast">'
        f'{message} <button onclick="this.closest(\'#toast\').remove()">×</button>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------

_static_dir = Path(__file__).parent / "static"


@router.get("/static/{filename}")
def get_static_file(filename: str):
    resolved = (_static_dir / filename).resolve()
    if _static_dir not in resolved.parents:
        return Response("Forbidden", status_code=403)
    if not resolved.is_file():
        return Response("Not Found", status_code=404)
    mimetype, _ = mimetypes.guess_type(resolved)
    return Response(resolved.read_bytes(), media_type=mimetype)


# ---------------------------------------------------------------------------
# SSE
# ---------------------------------------------------------------------------

class UISignalsQueue(ServerSideSignalsQueue):
    async def add_new_message(
        self,
        event: EventCallbacksManager.Events,
        uuid: str = "",
        data: str = "",
    ):
        if event == EventCallbacksManager.Events.RefreshInstance:
            inst = global_instances.get(uuid)
            uuid = inst.workflow_uuid if inst else uuid
        await super().add_new_message(event, uuid, data)


@router.get("/events")
async def sse_stream(request: Request):
    sse = UISignalsQueue(request)
    for ev in EventCallbacksManager.Events:
        eventsCallbackManager.register_callback(ev, sse.add_new_message)
    return EventSourceResponse(sse.message_generator())


# ---------------------------------------------------------------------------
# Full page
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
@router.get("", response_class=HTMLResponse)
def get_ui(request: Request):
    workflows = list(global_workflows.values())
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "workflows": workflows,
            "selected_uuid": None,
            "globals_dirty": _is_globals_draft_dirty(),
        },
    )


# ---------------------------------------------------------------------------
# Sidebar fragment
# ---------------------------------------------------------------------------

@router.get("/sidebar", response_class=HTMLResponse)
def get_sidebar(request: Request, selected_uuid: str = ""):
    return templates.TemplateResponse(
        "sidebar.html",
        {
            "request": request,
            "workflows": list(global_workflows.values()),
            "selected_uuid": selected_uuid,
            "globals_dirty": _is_globals_draft_dirty(),
        },
    )


# ---------------------------------------------------------------------------
# Workflow pane (full right pane)
# ---------------------------------------------------------------------------

@router.get("/workflow/{uuid}", response_class=HTMLResponse)
def get_workflow_pane(request: Request, uuid: str):
    wf = global_workflows.get(uuid)
    if not wf:
        return HTMLResponse("Workflow not found", status_code=404)
    ctx = _instances_context(wf)
    ctx["dirty"] = _is_draft_dirty(uuid)
    ctx["command_names"] = list(Commands.commands.keys())
    ctx["command_args"] = _command_args_for_template()
    return templates.TemplateResponse("workflow_pane.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Instances tab
# ---------------------------------------------------------------------------

@router.get("/workflow/{uuid}/instances", response_class=HTMLResponse)
def get_instances_tab(request: Request, uuid: str):
    wf = global_workflows.get(uuid)
    if not wf:
        return HTMLResponse("Workflow not found", status_code=404)
    ctx = _instances_context(wf)
    dirty = _is_draft_dirty(uuid)
    tab_bar = templates.get_template("partials/tab_bar.html").render(
        workflow_uuid=uuid, active_tab="instances", dirty=dirty
    )
    content = templates.get_template("workflow_instances.html").render(**ctx)
    return HTMLResponse(tab_bar + content)


# ---------------------------------------------------------------------------
# Design tab
# ---------------------------------------------------------------------------

@router.get("/workflow/{uuid}/design", response_class=HTMLResponse)
def get_design_tab(request: Request, uuid: str):
    draft = _get_or_create_workflow_draft(uuid)
    if not draft:
        return HTMLResponse("Workflow not found", status_code=404)
    ctx = _design_context(uuid, draft)
    dirty = ctx["dirty"]
    tab_bar = templates.get_template("partials/tab_bar.html").render(
        workflow_uuid=uuid, active_tab="design", dirty=dirty
    )
    content = templates.get_template("workflow_design.html").render(**ctx)
    return HTMLResponse(tab_bar + content)


# ---------------------------------------------------------------------------
# Global variables pane
# ---------------------------------------------------------------------------

@router.get("/globals", response_class=HTMLResponse)
def get_globals_pane(request: Request):
    draft = _get_or_create_globals_draft()
    return templates.TemplateResponse(
        "globals.html",
        {
            "request": request,
            "global_vars": draft,
            "var_types": _var_type_names(),
            "dirty": _is_globals_draft_dirty(),
        },
    )


# ---------------------------------------------------------------------------
# Workflow add
# ---------------------------------------------------------------------------

@router.post("/workflow/add", response_class=HTMLResponse)
async def add_workflow(request: Request):
    wf = Workflow()
    wf.uuid = str(uuid4())
    wf.name = "Untitled"
    global_workflows[wf.uuid] = wf
    workflow_drafts[wf.uuid] = deepcopy(wf)
    await eventsCallbackManager.signal_event(EventCallbacksManager.Events.RefreshWorkflows)
    pipelineManager.save_state()
    ctx = _design_context(wf.uuid, workflow_drafts[wf.uuid])
    content = templates.get_template("workflow_design.html").render(**ctx)
    tab_bar = templates.get_template("partials/tab_bar.html").render(
        workflow_uuid=wf.uuid, active_tab="design", dirty=False
    )
    return HTMLResponse(tab_bar + content)


# ---------------------------------------------------------------------------
# Workflow delete
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/delete", response_class=HTMLResponse)
async def delete_workflow(uuid: str):
    global_workflows.pop(uuid, None)
    workflow_drafts.pop(uuid, None)
    await eventsCallbackManager.signal_event(EventCallbacksManager.Events.RefreshWorkflows)
    pipelineManager.save_state()
    sidebar = templates.get_template("sidebar.html").render(
        workflows=list(global_workflows.values()),
        selected_uuid=None,
        globals_dirty=_is_globals_draft_dirty(),
    )
    # Return sidebar OOB + empty right pane
    sidebar_oob = sidebar.replace(
        '<div id="sidebar"', '<div id="sidebar" hx-swap-oob="outerHTML:#sidebar"', 1
    )
    return HTMLResponse(sidebar_oob + '<div id="right-pane-empty">Select a workflow from the sidebar</div>')


# ---------------------------------------------------------------------------
# Workflow toggle pause
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/toggle_pause", response_class=HTMLResponse)
async def toggle_workflow_pause(uuid: str):
    wf = global_workflows.get(uuid)
    if not wf:
        return HTMLResponse("Not found", status_code=404)
    wf.state = RunStates.Paused if wf.state == RunStates.Running else RunStates.Running
    await eventsCallbackManager.signal_event(EventCallbacksManager.Events.RefreshWorkflows)
    pipelineManager.save_state()
    sidebar = templates.get_template("sidebar.html").render(
        workflows=list(global_workflows.values()),
        selected_uuid=None,
        globals_dirty=_is_globals_draft_dirty(),
    )
    return HTMLResponse(sidebar)


# ---------------------------------------------------------------------------
# Workflow save (design tab)
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/save", response_class=HTMLResponse)
async def save_workflow(request: Request, uuid: str):
    draft = workflow_drafts.get(uuid)
    if not draft:
        return HTMLResponse("No draft found", status_code=404)
    saved = global_workflows.get(uuid)
    if not saved:
        return HTMLResponse("Workflow not found", status_code=404)

    form = await request.form()
    draft.name = (form.get("name") or "").strip() or "Untitled"
    draft.user_notes = form.get("user_notes") or ""

    # Preserve runtime state
    draft.state = saved.state

    # Flush draft → saved
    global_workflows[uuid] = deepcopy(draft)
    # Reset draft to freshly saved state
    workflow_drafts[uuid] = deepcopy(global_workflows[uuid])

    await eventsCallbackManager.signal_event(EventCallbacksManager.Events.RefreshWorkflows)
    pipelineManager.save_state()

    ctx = _design_context(uuid, workflow_drafts[uuid])
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Design discard
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/design/discard", response_class=HTMLResponse)
def discard_design(request: Request, uuid: str):
    if uuid in global_workflows:
        workflow_drafts[uuid] = deepcopy(global_workflows[uuid])
    ctx = _design_context(uuid, workflow_drafts[uuid])
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Instance spawn dialog
# ---------------------------------------------------------------------------

@router.get("/workflow/{uuid}/instances/spawn_dialog", response_class=HTMLResponse)
def spawn_dialog(request: Request, uuid: str):
    wf = global_workflows.get(uuid)
    if not wf:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse(
        "partials/spawn_dialog.html",
        {"request": request, "workflow": wf, "var_types": _var_type_names()},
    )


# ---------------------------------------------------------------------------
# Instance spawn
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/instances/spawn", response_class=HTMLResponse)
async def spawn_instance(request: Request, uuid: str):
    wf = global_workflows.get(uuid)
    if not wf:
        return HTMLResponse("Not found", status_code=404)

    form = await request.form()
    overrides: dict[str, WorkVariable] = {}
    for key, raw_val in form.items():
        if key.startswith("arg__"):
            var_name = key[5:]
            if var_name in wf.setup_variables:
                template_var = deepcopy(wf.setup_variables[var_name])
                try:
                    template_var.value = raw_val
                    template_var.normalize()
                except Exception:
                    pass
                overrides[var_name] = template_var

    inst = wf.spawn_instance(overrides)
    await pipelineManager.notify_of_something_happening()
    pipelineManager.save_state()

    ctx = _instances_context(wf)
    instances_html = templates.get_template("workflow_instances.html").render(**ctx)
    # Delete modal via OOB — empty replacement would still match the CSS rule and keep the backdrop
    modal_close = '<div id="spawn-modal" hx-swap-oob="delete"></div>'
    return HTMLResponse(instances_html + modal_close)


# ---------------------------------------------------------------------------
# Instance delete
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/instances/{iuuid}/delete", response_class=HTMLResponse)
async def delete_instance(uuid: str, iuuid: str):
    global_instances.pop(iuuid, None)
    pipelineManager.save_state()
    wf = global_workflows.get(uuid)
    if not wf:
        return HTMLResponse("Not found", status_code=404)
    ctx = _instances_context(wf)
    return HTMLResponse(templates.get_template("workflow_instances.html").render(**ctx))


# ---------------------------------------------------------------------------
# Instance toggle pause
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/instances/{iuuid}/toggle_pause", response_class=HTMLResponse)
async def toggle_instance_pause(uuid: str, iuuid: str):
    inst = global_instances.get(iuuid)
    if inst:
        inst.state = RunStates.Paused if inst.state == RunStates.Running else RunStates.Running
        pipelineManager.save_state()
    wf = global_workflows.get(uuid)
    if not wf:
        return HTMLResponse("Not found", status_code=404)
    ctx = _instances_context(wf)
    return HTMLResponse(templates.get_template("workflow_instances.html").render(**ctx))


# ---------------------------------------------------------------------------
# Design variable: add top-level variable
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/design/variable/add", response_class=HTMLResponse)
def design_var_add(request: Request, uuid: str, section: str = Form(...)):
    draft = _get_or_create_workflow_draft(uuid)
    if not draft:
        return HTMLResponse("Not found", status_code=404)
    section_vars = _section_vars(draft, section)
    base = "new_var"
    name = base
    counter = 1
    while name in section_vars:
        name = f"{base}_{counter}"
        counter += 1
    from pipeline_backend.variables import String
    section_vars[name] = String("")
    ctx = _design_context(uuid, draft)
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Design variable: delete top-level variable
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/design/variable/delete", response_class=HTMLResponse)
async def design_var_delete(request: Request, uuid: str):
    form = await request.form()
    section = form.get("section", "")
    var_name = form.get("var_name", "")
    draft = _get_or_create_workflow_draft(uuid)
    if not draft:
        return HTMLResponse("Not found", status_code=404)
    section_vars = _section_vars(draft, section)
    section_vars.pop(var_name, None)
    ctx = _design_context(uuid, draft)
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Design variable: change type
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/design/variable/type", response_class=HTMLResponse)
async def design_var_type(request: Request, uuid: str):
    form = await request.form()
    section = form.get("section", "")
    var_name = form.get("var_name", "")
    path = json.loads(form.get("path", "[]"))
    new_type_name = form.get("new_type", "")
    draft = _get_or_create_workflow_draft(uuid)
    if not draft:
        return HTMLResponse("Not found", status_code=404)
    section_vars = _section_vars(draft, section)
    if var_name not in section_vars:
        return HTMLResponse("Variable not found", status_code=404)

    try:
        new_type = WorkVariable.class_from_name(new_type_name)
    except TypeError as e:
        ctx = _design_context(uuid, draft)
        return templates.TemplateResponse(
            "workflow_design.html",
            {"request": request, **ctx},
            headers={"HX-Trigger": "toast"},
        )

    if not path:
        converted = section_vars[var_name].coerce_into_type(new_type)
        section_vars[var_name] = converted if converted is not None else new_type()
    else:
        # Navigate to parent container and change the nested entry's type
        target_var = section_vars[var_name]
        node = target_var
        for key in path[:-1]:
            node = node.value[key] if isinstance(key, int) else node.value[key]
        last_key = path[-1]
        existing = node.value[last_key]
        converted = existing.coerce_into_type(new_type)
        node.value[last_key] = converted if converted is not None else new_type()

    ctx = _design_context(uuid, draft)
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Design variable: add entry to container
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/design/variable/entry/add", response_class=HTMLResponse)
async def design_var_entry_add(request: Request, uuid: str):
    form = await request.form()
    section = form.get("section", "")
    var_name = form.get("var_name", "")
    path = json.loads(form.get("path", "[]"))
    key = form.get("key", None)  # for Dictionary entries
    draft = _get_or_create_workflow_draft(uuid)
    if not draft:
        return HTMLResponse("Not found", status_code=404)
    section_vars = _section_vars(draft, section)
    target = section_vars[var_name]
    # Navigate to the container at path
    node = target
    for k in path:
        node = node.value[k] if isinstance(k, int) else node.value[k]
    from pipeline_backend.variables import String
    if node.typename == "Dictionary":
        if not key:
            key = "new_key"
        base = key
        counter = 1
        while key in node.value:
            key = f"{base}_{counter}"
            counter += 1
        node.value[key] = String("")
    else:
        # VariableList or StringList / VariableNameList
        if node.typename in ("StringList", "VariableNameList"):
            node.value.append("")
        else:
            node.value.append(String(""))
    ctx = _design_context(uuid, draft)
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Design variable: delete entry from container
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/design/variable/entry/delete", response_class=HTMLResponse)
async def design_var_entry_delete(request: Request, uuid: str):
    form = await request.form()
    section = form.get("section", "")
    var_name = form.get("var_name", "")
    path = json.loads(form.get("path", "[]"))
    idx_raw = form.get("idx", None)
    key = form.get("key", None)
    draft = _get_or_create_workflow_draft(uuid)
    if not draft:
        return HTMLResponse("Not found", status_code=404)
    section_vars = _section_vars(draft, section)
    target = section_vars[var_name]
    node = target
    for k in path:
        node = node.value[k] if isinstance(k, int) else node.value[k]
    if key is not None:
        node.value.pop(key, None)
    elif idx_raw is not None:
        del node.value[int(idx_raw)]
    ctx = _design_context(uuid, draft)
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Procedure: add
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/procedure/add", response_class=HTMLResponse)
def procedure_add(request: Request, uuid: str):
    draft = _get_or_create_workflow_draft(uuid)
    if not draft:
        return HTMLResponse("Not found", status_code=404)
    base = "procedure"
    name = base
    counter = 1
    while name in draft.procedures:
        name = f"{base}_{counter}"
        counter += 1
    first_cmd = next(iter(Commands.commands), "")
    draft.procedures[name] = [ProcessingStep(first_cmd)] if first_cmd else [ProcessingStep()]
    ctx = _design_context(uuid, draft)
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Procedure: delete
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/procedure/delete", response_class=HTMLResponse)
async def procedure_delete(request: Request, uuid: str):
    form = await request.form()
    proc_name = form.get("proc_name", "")
    draft = _get_or_create_workflow_draft(uuid)
    if not draft:
        return HTMLResponse("Not found", status_code=404)
    if proc_name != "start":
        draft.procedures.pop(proc_name, None)
    ctx = _design_context(uuid, draft)
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Procedure: rename
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/procedure/rename", response_class=HTMLResponse)
async def procedure_rename(request: Request, uuid: str):
    form = await request.form()
    proc_name = form.get("proc_name", "")
    new_name = (form.get("new_name") or "").strip()
    draft = _get_or_create_workflow_draft(uuid)
    if not draft:
        return HTMLResponse("Not found", status_code=404)

    ctx = _design_context(uuid, draft)
    if not new_name:
        toast = _toast_oob("Procedure name cannot be empty.")
        content = templates.get_template("workflow_design.html").render(**ctx)
        return HTMLResponse(content + toast)
    if new_name in draft.procedures:
        toast = _toast_oob(f"Procedure '{new_name}' already exists.")
        content = templates.get_template("workflow_design.html").render(**ctx)
        return HTMLResponse(content + toast)

    # Rebuild ordered dict with renamed key
    new_procs = {}
    for k, v in draft.procedures.items():
        new_procs[new_name if k == proc_name else k] = v
    draft.procedures = new_procs
    ctx = _design_context(uuid, draft)
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Procedure step: add
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/procedure/step/add", response_class=HTMLResponse)
async def step_add(request: Request, uuid: str):
    form = await request.form()
    proc_name = form.get("proc_name", "")
    draft = _get_or_create_workflow_draft(uuid)
    if not draft or proc_name not in draft.procedures:
        return HTMLResponse("Not found", status_code=404)
    first_cmd = next(iter(Commands.commands), "")
    draft.procedures[proc_name].append(ProcessingStep(first_cmd) if first_cmd else ProcessingStep())
    ctx = _design_context(uuid, draft)
    # Re-render just the procedure section
    proc_html = _render_procedure_section(uuid, draft, proc_name, ctx)
    return HTMLResponse(proc_html)


# ---------------------------------------------------------------------------
# Procedure step: delete
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/procedure/step/delete", response_class=HTMLResponse)
async def step_delete(request: Request, uuid: str):
    form = await request.form()
    proc_name = form.get("proc_name", "")
    idx = int(form.get("idx", 0))
    draft = _get_or_create_workflow_draft(uuid)
    if not draft or proc_name not in draft.procedures:
        return HTMLResponse("Not found", status_code=404)
    steps = draft.procedures[proc_name]
    if 0 <= idx < len(steps):
        del steps[idx]
    ctx = _design_context(uuid, draft)
    return HTMLResponse(_render_procedure_section(uuid, draft, proc_name, ctx))


# ---------------------------------------------------------------------------
# Procedure step: change command
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/procedure/step/command", response_class=HTMLResponse)
async def step_command(request: Request, uuid: str):
    form = await request.form()
    proc_name = form.get("proc_name", "")
    idx = int(form.get("idx", 0))
    command_name = form.get("command_name", "")
    draft = _get_or_create_workflow_draft(uuid)
    if not draft or proc_name not in draft.procedures:
        return HTMLResponse("Not found", status_code=404)
    steps = draft.procedures[proc_name]
    if 0 <= idx < len(steps):
        steps[idx] = ProcessingStep(command_name)
    ctx = _design_context(uuid, draft)
    # Re-render just this one step row
    step = steps[idx]
    step_html = templates.get_template("partials/step_row.html").render(
        step=step,
        step_idx=idx,
        workflow_uuid=uuid,
        proc_name=proc_name,
        command_names=ctx["command_names"],
        command_args=ctx["command_args"],
    )
    return HTMLResponse(step_html)


# ---------------------------------------------------------------------------
# Procedure steps: reorder
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/procedure/steps/reorder", response_class=HTMLResponse)
async def steps_reorder(request: Request, uuid: str):
    form = await request.form()
    proc_name = form.get("proc_name", "")
    order = json.loads(form.get("order", "[]"))
    draft = _get_or_create_workflow_draft(uuid)
    if not draft or proc_name not in draft.procedures:
        return HTMLResponse("Not found", status_code=404)
    steps = draft.procedures[proc_name]
    try:
        new_order = [int(i) for i in order]
        draft.procedures[proc_name] = [steps[i] for i in new_order if 0 <= i < len(steps)]
    except (ValueError, IndexError):
        pass
    ctx = _design_context(uuid, draft)
    return HTMLResponse(_render_procedure_section(uuid, draft, proc_name, ctx))


# ---------------------------------------------------------------------------
# Globals: save
# ---------------------------------------------------------------------------

@router.post("/globals/save", response_class=HTMLResponse)
async def globals_save(request: Request):
    global globals_draft
    draft = _get_or_create_globals_draft()
    global_variables.clear()
    global_variables.update(deepcopy(draft))
    globals_draft = deepcopy(global_variables)
    pipelineManager.save_state()
    return templates.TemplateResponse(
        "globals.html",
        {
            "request": request,
            "global_vars": globals_draft,
            "var_types": _var_type_names(),
            "dirty": False,
        },
    )


# ---------------------------------------------------------------------------
# Globals: discard
# ---------------------------------------------------------------------------

@router.post("/globals/discard", response_class=HTMLResponse)
def globals_discard(request: Request):
    global globals_draft
    globals_draft = deepcopy(global_variables)
    return templates.TemplateResponse(
        "globals.html",
        {
            "request": request,
            "global_vars": globals_draft,
            "var_types": _var_type_names(),
            "dirty": False,
        },
    )


# ---------------------------------------------------------------------------
# Globals variable: add
# ---------------------------------------------------------------------------

@router.post("/globals/variable/add", response_class=HTMLResponse)
def globals_var_add(request: Request):
    from pipeline_backend.variables import String
    draft = _get_or_create_globals_draft()
    base = "new_var"
    name = base
    counter = 1
    while name in draft:
        name = f"{base}_{counter}"
        counter += 1
    draft[name] = String("")
    return templates.TemplateResponse(
        "globals.html",
        {
            "request": request,
            "global_vars": draft,
            "var_types": _var_type_names(),
            "dirty": _is_globals_draft_dirty(),
        },
    )


# ---------------------------------------------------------------------------
# Globals variable: delete
# ---------------------------------------------------------------------------

@router.post("/globals/variable/delete", response_class=HTMLResponse)
async def globals_var_delete(request: Request):
    form = await request.form()
    var_name = form.get("var_name", "")
    draft = _get_or_create_globals_draft()
    draft.pop(var_name, None)
    return templates.TemplateResponse(
        "globals.html",
        {
            "request": request,
            "global_vars": draft,
            "var_types": _var_type_names(),
            "dirty": _is_globals_draft_dirty(),
        },
    )


# ---------------------------------------------------------------------------
# Globals variable: change type
# ---------------------------------------------------------------------------

@router.post("/globals/variable/type", response_class=HTMLResponse)
async def globals_var_type(request: Request):
    form = await request.form()
    var_name = form.get("var_name", "")
    path = json.loads(form.get("path", "[]"))
    new_type_name = form.get("new_type", "")
    draft = _get_or_create_globals_draft()
    if var_name not in draft:
        return HTMLResponse("Not found", status_code=404)
    try:
        new_type = WorkVariable.class_from_name(new_type_name)
    except TypeError:
        pass
    else:
        if not path:
            converted = draft[var_name].coerce_into_type(new_type)
            draft[var_name] = converted if converted is not None else new_type()
        else:
            node = draft[var_name]
            for k in path[:-1]:
                node = node.value[k] if isinstance(k, int) else node.value[k]
            last_key = path[-1]
            existing = node.value[last_key]
            converted = existing.coerce_into_type(new_type)
            node.value[last_key] = converted if converted is not None else new_type()
    return templates.TemplateResponse(
        "globals.html",
        {
            "request": request,
            "global_vars": draft,
            "var_types": _var_type_names(),
            "dirty": _is_globals_draft_dirty(),
        },
    )


# ---------------------------------------------------------------------------
# Globals variable: add/delete entries (containers)
# ---------------------------------------------------------------------------

@router.post("/globals/variable/entry/add", response_class=HTMLResponse)
async def globals_entry_add(request: Request):
    form = await request.form()
    var_name = form.get("var_name", "")
    path = json.loads(form.get("path", "[]"))
    key = form.get("key", None)
    draft = _get_or_create_globals_draft()
    if var_name not in draft:
        return HTMLResponse("Not found", status_code=404)
    node = draft[var_name]
    for k in path:
        node = node.value[k] if isinstance(k, int) else node.value[k]
    from pipeline_backend.variables import String
    if node.typename == "Dictionary":
        if not key:
            key = "new_key"
        base = key
        counter = 1
        while key in node.value:
            key = f"{base}_{counter}"
            counter += 1
        node.value[key] = String("")
    elif node.typename in ("StringList", "VariableNameList"):
        node.value.append("")
    else:
        node.value.append(String(""))
    return templates.TemplateResponse(
        "globals.html",
        {
            "request": request,
            "global_vars": draft,
            "var_types": _var_type_names(),
            "dirty": _is_globals_draft_dirty(),
        },
    )


@router.post("/globals/variable/entry/delete", response_class=HTMLResponse)
async def globals_entry_delete(request: Request):
    form = await request.form()
    var_name = form.get("var_name", "")
    path = json.loads(form.get("path", "[]"))
    idx_raw = form.get("idx", None)
    key = form.get("key", None)
    draft = _get_or_create_globals_draft()
    if var_name not in draft:
        return HTMLResponse("Not found", status_code=404)
    node = draft[var_name]
    for k in path:
        node = node.value[k] if isinstance(k, int) else node.value[k]
    if key is not None:
        node.value.pop(key, None)
    elif idx_raw is not None:
        del node.value[int(idx_raw)]
    return templates.TemplateResponse(
        "globals.html",
        {
            "request": request,
            "global_vars": draft,
            "var_types": _var_type_names(),
            "dirty": _is_globals_draft_dirty(),
        },
    )


# ---------------------------------------------------------------------------
# Helper: render a single procedure section HTML string
# ---------------------------------------------------------------------------

def _render_procedure_section(uuid: str, draft: Workflow, proc_name: str, ctx: dict) -> str:
    steps = draft.procedures.get(proc_name, [])
    return templates.get_template("partials/procedure_section.html").render(
        proc_name=proc_name,
        steps=steps,
        workflow_uuid=uuid,
        command_names=ctx["command_names"],
        command_args=ctx["command_args"],
        is_start=(proc_name == "start"),
    )
