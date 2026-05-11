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
from pipeline_backend.instances import Instance
from pipeline_backend.manager import pipelineManager
from pipeline_backend.variables import WorkVariable
from pipeline_backend.workflows import RunStates, Workflow, ProcessingStep

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
# Draft state — workflow
# ---------------------------------------------------------------------------

workflow_drafts: dict[str, Workflow] = {}


def _get_or_create_workflow_draft(uuid: str) -> Workflow | None:
    if uuid not in pipelineManager.ctx.workflows:
        return None
    if uuid not in workflow_drafts:
        workflow_drafts[uuid] = deepcopy(pipelineManager.ctx.workflows[uuid])
    return workflow_drafts[uuid]


def _is_draft_dirty(uuid: str) -> bool:
    if uuid not in workflow_drafts or uuid not in pipelineManager.ctx.workflows:
        return False
    return pipelineManager.ctx.workflows[uuid].json_savable() != workflow_drafts[uuid].json_savable()


# ---------------------------------------------------------------------------
# Variable store (unified draft/dirty/persist for globals, secrets, …)
# ---------------------------------------------------------------------------

class VariableStore:
    def __init__(
        self,
        live: dict,
        ctx_type: str,
        prefix: str,
        pane_id: str,
        dirty_label_id: str,
        title: str,
        default_new_name: str,
        add_btn_label: str,
        empty_msg: str,
        persist_fn,
        description: str = "",
    ):
        self.live = live
        self.ctx_type = ctx_type
        self.prefix = prefix
        self.pane_id = pane_id
        self.dirty_label_id = dirty_label_id
        self.title = title
        self.default_new_name = default_new_name
        self.add_btn_label = add_btn_label
        self.empty_msg = empty_msg
        self.persist_fn = persist_fn
        self.description = description
        self._draft: dict | None = None

    @property
    def draft(self) -> dict:
        if self._draft is None:
            self._draft = deepcopy(self.live)
        return self._draft

    def is_dirty(self) -> bool:
        if self._draft is None:
            return False
        return (
            {k: v.json_savable() for k, v in self._draft.items()}
            != {k: v.json_savable() for k, v in self.live.items()}
        )

    def save(self) -> None:
        self.live.clear()
        self.live.update(deepcopy(self._draft))
        self._draft = deepcopy(self.live)
        self.persist_fn()

    def discard(self) -> None:
        self._draft = deepcopy(self.live)

    def _ctx(self) -> dict:
        return {
            "vars": self.draft,
            "var_types": _var_type_names(),
            "dirty": self.is_dirty(),
            "ctx_type": self.ctx_type,
            "prefix": self.prefix,
            "pane_id": self.pane_id,
            "dirty_label_id": self.dirty_label_id,
            "title": self.title,
            "add_btn_label": self.add_btn_label,
            "empty_msg": self.empty_msg,
            "description": self.description,
        }

    def render(self, request: Request):
        return templates.TemplateResponse(
            "variable_store_pane.html", {"request": request, **self._ctx()}
        )

    def render_html(self) -> str:
        return templates.get_template("variable_store_pane.html").render(**self._ctx())


globals_store = VariableStore(
    live=pipelineManager.ctx.variables,
    ctx_type="global",
    prefix="/ui/globals",
    pane_id="globals-pane",
    dirty_label_id="globals-dirty-label",
    title="Global Variables",
    default_new_name="new_var",
    add_btn_label="+ Add Variable",
    empty_msg="No global variables.",
    persist_fn=pipelineManager.save_state,
)

secrets_store = VariableStore(
    live=pipelineManager.ctx.secrets,
    ctx_type="secret",
    prefix="/ui/secrets",
    pane_id="secrets-pane",
    dirty_label_id="secrets-dirty-label",
    title="Secrets",
    default_new_name="new_secret",
    add_btn_label="+ Add Secret",
    empty_msg="No secrets defined.",
    persist_fn=pipelineManager.save_secrets,
    description=(
        "Secrets are stored in a separate file and are never included in the main "
        "pipeline state export. Reference them by name from workflows just like global variables."
    ),
)

# ---------------------------------------------------------------------------
# Helper: list of all WorkVariable type names
# ---------------------------------------------------------------------------

def _var_type_names() -> list[str]:
    return [cls.__name__ for cls in WorkVariable.__subclasses__()]


# ---------------------------------------------------------------------------
# Helper: command arg info for templates
# command_args: dict[cmd_name -> list[(arg_name, type_str_or_list)]]
# ---------------------------------------------------------------------------

def _command_docstrings_for_template() -> dict:
    return {name: Commands.get_command_doc_string(name) for name in Commands.commands}


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
        "command_groups": Commands.get_commands_grouped(),
        "command_args": _command_args_for_template(),
        "command_docs": _command_docstrings_for_template(),
        "dirty": _is_draft_dirty(workflow_uuid),
        "active_tab": "design",
    }


def _instances_context(workflow: Workflow) -> dict:
    insts = [i for i in pipelineManager.ctx.instances.values() if i.workflow_uuid == workflow.uuid]
    return {
        "workflow": workflow,
        "workflow_uuid": workflow.uuid,
        "instances": insts,
        "var_types": _var_type_names(),
        "active_tab": "instances",
    }


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
# Shared variable mutation helpers (operate on a raw dict[str, WorkVariable])
# ---------------------------------------------------------------------------

def _vars_add(vars_dict: dict, default_name: str) -> None:
    from pipeline_backend.variables import String
    base = default_name
    name = base
    counter = 1
    while name in vars_dict:
        name = f"{base}_{counter}"
        counter += 1
    vars_dict[name] = String("")


def _vars_delete(vars_dict: dict, var_name: str) -> None:
    vars_dict.pop(var_name, None)


def _vars_rename(vars_dict: dict, old_name: str, new_name: str) -> None:
    if new_name and new_name != old_name and old_name in vars_dict and new_name not in vars_dict:
        renamed = {(new_name if k == old_name else k): v for k, v in vars_dict.items()}
        vars_dict.clear()
        vars_dict.update(renamed)


def _apply_value_to_node(node, last_key, raw_value: str) -> None:
    """Write raw_value into node.value[last_key], handling both WorkVariable and plain str entries."""
    existing = node.value[last_key]
    if isinstance(existing, WorkVariable):
        existing.value = raw_value
        try:
            existing.normalize()
        except Exception:
            pass
    else:
        # Plain string entry (StringList / VariableNameList)
        node.value[last_key] = str(raw_value).strip()


def _vars_value(vars_dict: dict, var_name: str, path: list, raw_val: str) -> None:
    if var_name not in vars_dict:
        return
    target = vars_dict[var_name]
    if not path:
        target.value = raw_val
        try:
            target.normalize()
        except Exception:
            pass
    else:
        node = target
        for k in path[:-1]:
            node = node.value[int(k)] if isinstance(k, int) else node.value[k]
        last_key = path[-1]
        if isinstance(last_key, str) and last_key.lstrip("-").isdigit():
            last_key = int(last_key)
        _apply_value_to_node(node, last_key, raw_val)


def _vars_type(vars_dict: dict, var_name: str, path: list, new_type_name: str) -> bool:
    """Apply a type change. Returns False if new_type_name is invalid."""
    if var_name not in vars_dict:
        return True
    try:
        new_type = WorkVariable.class_from_name(new_type_name)
    except TypeError:
        return False
    if not path:
        converted = vars_dict[var_name].coerce_into_type(new_type)
        vars_dict[var_name] = converted if converted is not None else new_type()
    else:
        node = vars_dict[var_name]
        for k in path[:-1]:
            node = node.value[k] if isinstance(k, int) else node.value[k]
        last_key = path[-1]
        existing = node.value[last_key]
        converted = existing.coerce_into_type(new_type)
        node.value[last_key] = converted if converted is not None else new_type()
    return True


def _vars_entry_add(vars_dict: dict, var_name: str, path: list, key) -> None:
    if var_name not in vars_dict:
        return
    from pipeline_backend.variables import String
    node = vars_dict[var_name]
    for k in path:
        node = node.value[k] if isinstance(k, int) else node.value[k]
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


def _vars_entry_delete(vars_dict: dict, var_name: str, path: list, idx_raw, key) -> None:
    if var_name not in vars_dict:
        return
    node = vars_dict[var_name]
    for k in path:
        node = node.value[k] if isinstance(k, int) else node.value[k]
    if key is not None:
        node.value.pop(key, None)
    elif idx_raw is not None:
        del node.value[int(idx_raw)]


def _vars_entry_reorder(vars_dict: dict, var_name: str, path: list, order: list) -> None:
    if var_name not in vars_dict:
        return
    node = vars_dict[var_name]
    for k in path:
        node = node.value[k] if isinstance(k, int) else node.value[k]
    try:
        new_order = [int(i) for i in order]
        node.value = [node.value[i] for i in new_order if 0 <= i < len(node.value)]
    except (ValueError, IndexError):
        pass


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
            inst = pipelineManager.ctx.instances.get(uuid)
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
    workflows = list(pipelineManager.ctx.workflows.values())
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "workflows": workflows,
            "selected_uuid": None,
            "globals_dirty": globals_store.is_dirty(),
            "secrets_dirty": secrets_store.is_dirty(),
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
            "workflows": list(pipelineManager.ctx.workflows.values()),
            "selected_uuid": selected_uuid,
            "globals_dirty": globals_store.is_dirty(),
            "secrets_dirty": secrets_store.is_dirty(),
        },
    )


# ---------------------------------------------------------------------------
# Workflow pane (full right pane)
# ---------------------------------------------------------------------------

@router.get("/workflow/{uuid}", response_class=HTMLResponse)
def get_workflow_pane(request: Request, uuid: str):
    wf = pipelineManager.ctx.workflows.get(uuid)
    if not wf:
        return HTMLResponse("Workflow not found", status_code=404)
    ctx = _instances_context(wf)
    ctx["dirty"] = _is_draft_dirty(uuid)
    ctx["command_groups"] = Commands.get_commands_grouped()
    ctx["command_args"] = _command_args_for_template()
    ctx["command_docs"] = _command_docstrings_for_template()
    return templates.TemplateResponse("workflow_pane.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Instances tab
# ---------------------------------------------------------------------------

@router.get("/workflow/{uuid}/instances", response_class=HTMLResponse)
def get_instances_tab(request: Request, uuid: str):
    wf = pipelineManager.ctx.workflows.get(uuid)
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
    return globals_store.render(request)


# ---------------------------------------------------------------------------
# Secrets pane
# ---------------------------------------------------------------------------

@router.get("/secrets", response_class=HTMLResponse)
def get_secrets_pane(request: Request):
    return secrets_store.render(request)


# ---------------------------------------------------------------------------
# Workflow add
# ---------------------------------------------------------------------------

@router.post("/workflow/add", response_class=HTMLResponse)
async def add_workflow(request: Request):
    wf = Workflow(pipelineManager.ctx)
    wf.uuid = str(uuid4())
    wf.name = "Untitled"
    pipelineManager.ctx.workflows[wf.uuid] = wf
    await eventsCallbackManager.signal_event(EventCallbacksManager.Events.RefreshWorkflows)
    pipelineManager.save_state()
    return HTMLResponse("")


# ---------------------------------------------------------------------------
# Workflow delete
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/delete", response_class=HTMLResponse)
async def delete_workflow(uuid: str):
    pipelineManager.ctx.workflows.pop(uuid, None)
    workflow_drafts.pop(uuid, None)
    await eventsCallbackManager.signal_event(EventCallbacksManager.Events.RefreshWorkflows)
    pipelineManager.save_state()
    sidebar = templates.get_template("sidebar.html").render(
        workflows=list(pipelineManager.ctx.workflows.values()),
        selected_uuid=None,
        globals_dirty=globals_store.is_dirty(),
        secrets_dirty=secrets_store.is_dirty(),
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
    wf = pipelineManager.ctx.workflows.get(uuid)
    if not wf:
        return HTMLResponse("Not found", status_code=404)
    wf.state = RunStates.Paused if wf.state == RunStates.Running else RunStates.Running
    await eventsCallbackManager.signal_event(EventCallbacksManager.Events.RefreshWorkflows)
    pipelineManager.save_state()
    if wf.state == RunStates.Running:
        await pipelineManager.notify_of_something_happening()
    sidebar = templates.get_template("sidebar.html").render(
        workflows=list(pipelineManager.ctx.workflows.values()),
        selected_uuid=None,
        globals_dirty=globals_store.is_dirty(),
        secrets_dirty=secrets_store.is_dirty(),
    )
    return HTMLResponse(sidebar)


# ---------------------------------------------------------------------------
# Helpers: step variable access + initialisation
# ---------------------------------------------------------------------------

def _get_step_from_draft(draft, proc_name: str, step_idx: int):
    if not draft or proc_name not in draft.procedures:
        return None
    steps = draft.procedures[proc_name]
    return steps[step_idx] if step_idx < len(steps) else None


def _ensure_step_var(step, var_name: str) -> None:
    """Initialise var_name in step.variables from the command signature if absent."""
    if var_name in step.variables:
        return
    for a_name, a_types in Commands.get_command_input_variables(step.command_name):
        if a_name == var_name:
            cls = a_types if not isinstance(a_types, tuple) else a_types[0]
            if isinstance(cls, str):
                try:
                    cls = WorkVariable.class_from_name(cls)
                except TypeError:
                    return
            step.variables[var_name] = cls()
            return


# ---------------------------------------------------------------------------
# Context resolver: maps ctx_type → (vars_dict, render_fn, ensure_fn)
# ---------------------------------------------------------------------------

def _ctx_resolve(form):
    """
    Decode the ctx_type/ctx_* fields submitted by every var_row request and
    return (vars_dict, render_fn, ensure_fn) or None on failure.
      vars_dict  – the dict[str, WorkVariable] to mutate
      render_fn  – callable() → HTML string for the structural fragment
      ensure_fn  – callable(var_name) → ensures the variable exists before mutation
    """
    ctx_type = form.get("ctx_type", "")

    if ctx_type == "wf_var":
        uuid = form.get("ctx_uuid", "")
        section = form.get("ctx_section", "")
        draft = _get_or_create_workflow_draft(uuid)
        if not draft:
            return None
        try:
            vars_dict = _section_vars(draft, section)
        except ValueError:
            return None
        def render():
            ctx = _design_context(uuid, draft)
            return templates.get_template("workflow_design.html").render(**ctx)
        def ensure(var_name): pass
        return vars_dict, render, ensure

    elif ctx_type == "step_arg":
        uuid = form.get("ctx_uuid", "")
        proc_name = form.get("ctx_proc", "")
        step_idx = int(form.get("ctx_step", 0))
        draft = _get_or_create_workflow_draft(uuid)
        step = _get_step_from_draft(draft, proc_name, step_idx)
        if not step:
            return None
        def render():
            ctx = _design_context(uuid, draft)
            return _render_step_row(uuid, draft, proc_name, step_idx, ctx)
        def ensure(var_name):
            _ensure_step_var(step, var_name)
        return step.variables, render, ensure

    elif ctx_type == "global":
        def render(): return globals_store.render_html()
        def ensure(var_name): pass
        return globals_store.draft, render, ensure

    elif ctx_type == "secret":
        def render(): return secrets_store.render_html()
        def ensure(var_name): pass
        return secrets_store.draft, render, ensure

    return None


# ---------------------------------------------------------------------------
# Unified variable mutation endpoints (all var_row operations)
# ---------------------------------------------------------------------------

@router.post("/variable/value")
async def variable_value(request: Request):
    form = await request.form()
    result = _ctx_resolve(form)
    if not result:
        return Response(status_code=204)
    vars_dict, _, ensure = result
    var_name = form.get("var_name", "")
    path = json.loads(form.get("path") or "[]")
    ensure(var_name)
    _vars_value(vars_dict, var_name, path, form.get("value", ""))
    return Response(status_code=204)


@router.post("/variable/type", response_class=HTMLResponse)
async def variable_type(request: Request):
    form = await request.form()
    result = _ctx_resolve(form)
    if not result:
        return Response(status_code=204)
    vars_dict, render, ensure = result
    var_name = form.get("var_name", "")
    path = json.loads(form.get("path") or "[]")
    new_type_name = form.get("new_type", "")
    ensure(var_name)
    if var_name not in vars_dict and not path:
        try:
            vars_dict[var_name] = WorkVariable.class_from_name(new_type_name)()
        except TypeError:
            pass
    else:
        _vars_type(vars_dict, var_name, path, new_type_name)
    return HTMLResponse(render())


@router.post("/variable/delete", response_class=HTMLResponse)
async def variable_delete(request: Request):
    form = await request.form()
    result = _ctx_resolve(form)
    if not result:
        return Response(status_code=204)
    vars_dict, render, _ = result
    _vars_delete(vars_dict, form.get("var_name", ""))
    return HTMLResponse(render())


@router.post("/variable/rename", response_class=HTMLResponse)
async def variable_rename(request: Request):
    form = await request.form()
    result = _ctx_resolve(form)
    if not result:
        return Response(status_code=204)
    vars_dict, render, _ = result
    _vars_rename(vars_dict, form.get("old_name", ""), (form.get("new_name") or "").strip())
    return HTMLResponse(render())


@router.post("/variable/entry/add", response_class=HTMLResponse)
async def variable_entry_add(request: Request):
    form = await request.form()
    result = _ctx_resolve(form)
    if not result:
        return Response(status_code=204)
    vars_dict, render, ensure = result
    var_name = form.get("var_name", "")
    path = json.loads(form.get("path") or "[]")
    ensure(var_name)
    _vars_entry_add(vars_dict, var_name, path, form.get("key", None))
    return HTMLResponse(render())


@router.post("/variable/entry/delete", response_class=HTMLResponse)
async def variable_entry_delete(request: Request):
    form = await request.form()
    result = _ctx_resolve(form)
    if not result:
        return Response(status_code=204)
    vars_dict, render, _ = result
    var_name = form.get("var_name", "")
    path = json.loads(form.get("path") or "[]")
    _vars_entry_delete(vars_dict, var_name, path, form.get("idx", None), form.get("key", None))
    return HTMLResponse(render())


@router.post("/variable/entry/reorder", response_class=HTMLResponse)
async def variable_entry_reorder(request: Request):
    form = await request.form()
    result = _ctx_resolve(form)
    if not result:
        return Response(status_code=204)
    vars_dict, render, _ = result
    var_name = form.get("var_name", "")
    path = json.loads(form.get("path") or "[]")
    _vars_entry_reorder(vars_dict, var_name, path, json.loads(form.get("order", "[]")))
    return HTMLResponse(render())


# ---------------------------------------------------------------------------
# Workflow save (design tab)
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/save", response_class=HTMLResponse)
async def save_workflow(request: Request, uuid: str):
    draft = workflow_drafts.get(uuid)
    if not draft:
        return HTMLResponse("No draft found", status_code=404)
    saved = pipelineManager.ctx.workflows.get(uuid)
    if not saved:
        return HTMLResponse("Workflow not found", status_code=404)

    form = await request.form()
    draft.name = (form.get("name") or "").strip() or "Untitled"
    draft.user_notes = form.get("user_notes") or ""

    # Preserve runtime state
    draft.state = saved.state

    # Flush draft → saved
    pipelineManager.ctx.workflows[uuid] = deepcopy(draft)
    # Reset draft to freshly saved state
    workflow_drafts[uuid] = deepcopy(pipelineManager.ctx.workflows[uuid])

    await eventsCallbackManager.signal_event(EventCallbacksManager.Events.RefreshWorkflows)
    pipelineManager.save_state()

    ctx = _design_context(uuid, workflow_drafts[uuid])
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Design discard
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/design/discard", response_class=HTMLResponse)
def discard_design(request: Request, uuid: str):
    if uuid in pipelineManager.ctx.workflows:
        workflow_drafts[uuid] = deepcopy(pipelineManager.ctx.workflows[uuid])
    ctx = _design_context(uuid, workflow_drafts[uuid])
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})


# ---------------------------------------------------------------------------
# Instance spawn dialog
# ---------------------------------------------------------------------------

@router.get("/workflow/{uuid}/instances/spawn_dialog", response_class=HTMLResponse)
def spawn_dialog(request: Request, uuid: str):
    wf = pipelineManager.ctx.workflows.get(uuid)
    if not wf:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse(
        "partials/spawn_dialog.html",
        {"request": request, "workflow": wf, "var_types": _var_type_names()},
    )


# ---------------------------------------------------------------------------
# Single instance row (polled by expanded running instances)
# ---------------------------------------------------------------------------

@router.get("/workflow/{uuid}/instances/{iuuid}", response_class=HTMLResponse)
def get_instance_row(request: Request, uuid: str, iuuid: str):
    inst = pipelineManager.ctx.instances.get(iuuid)
    if not inst:
        return HTMLResponse("", status_code=200)
    return HTMLResponse(templates.get_template("partials/instance_row.html").render(
        inst=inst,
        workflow_uuid=uuid,
        var_types=_var_type_names(),
    ))


# ---------------------------------------------------------------------------
# Instance spawn
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/instances/spawn", response_class=HTMLResponse)
async def spawn_instance(request: Request, uuid: str):
    wf = pipelineManager.ctx.workflows.get(uuid)
    if not wf:
        return HTMLResponse("Not found", status_code=404)

    form = await request.form()
    overrides: dict[str, WorkVariable] = {}
    for key, raw_val in form.items():
        if key.startswith("arg__"):
            var_name = key[5:]
            if var_name in wf.setup_variables:
                argtype = form.get(f"argtype__{var_name}")
                try:
                    cls = WorkVariable.class_from_name(argtype) if argtype else None
                except TypeError:
                    cls = None
                if cls is None:
                    cls = wf.setup_variables[var_name].__class__
                var = cls()
                var.value = raw_val
                try:
                    var.normalize()
                except Exception:
                    pass
                overrides[var_name] = var

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
    pipelineManager.ctx.instances.pop(iuuid, None)
    pipelineManager.save_state()
    wf = pipelineManager.ctx.workflows.get(uuid)
    if not wf:
        return HTMLResponse("Not found", status_code=404)
    ctx = _instances_context(wf)
    return HTMLResponse(templates.get_template("workflow_instances.html").render(**ctx))


# ---------------------------------------------------------------------------
# Instance toggle pause
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/instances/{iuuid}/toggle_pause", response_class=HTMLResponse)
async def toggle_instance_pause(uuid: str, iuuid: str):
    inst = pipelineManager.ctx.instances.get(iuuid)
    if inst:
        inst.state = RunStates.Paused if inst.state == RunStates.Running else RunStates.Running
        pipelineManager.save_state()
        if inst.state == RunStates.Running:
            await pipelineManager.notify_of_something_happening()
    wf = pipelineManager.ctx.workflows.get(uuid)
    if not wf:
        return HTMLResponse("Not found", status_code=404)
    ctx = _instances_context(wf)
    return HTMLResponse(templates.get_template("workflow_instances.html").render(**ctx))


# ---------------------------------------------------------------------------
# Design variable: add / rename / delete / type / entry operations
# ---------------------------------------------------------------------------

@router.post("/workflow/{uuid}/design/variable/add", response_class=HTMLResponse)
def design_var_add(request: Request, uuid: str, section: str = Form(...)):
    draft = _get_or_create_workflow_draft(uuid)
    if not draft:
        return HTMLResponse("Not found", status_code=404)
    _vars_add(_section_vars(draft, section), "new_var")
    ctx = _design_context(uuid, draft)
    return templates.TemplateResponse("workflow_design.html", {"request": request, **ctx})




# ---------------------------------------------------------------------------
# Procedure: add / delete / rename
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
# Procedure step: add / delete / command / reorder
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
    return HTMLResponse(_render_step_row(uuid, draft, proc_name, idx, ctx))


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
# Globals: save / discard / variable CRUD
# ---------------------------------------------------------------------------

@router.post("/globals/save", response_class=HTMLResponse)
async def globals_save(request: Request):
    globals_store.save()
    return globals_store.render(request)


@router.post("/globals/discard", response_class=HTMLResponse)
def globals_discard(request: Request):
    globals_store.discard()
    return globals_store.render(request)


@router.post("/globals/variable/add", response_class=HTMLResponse)
def globals_var_add(request: Request):
    _vars_add(globals_store.draft, globals_store.default_new_name)
    return globals_store.render(request)




# ---------------------------------------------------------------------------
# Secrets: save / discard / variable CRUD
# ---------------------------------------------------------------------------

@router.post("/secrets/save", response_class=HTMLResponse)
async def secrets_save(request: Request):
    secrets_store.save()
    return secrets_store.render(request)


@router.post("/secrets/discard", response_class=HTMLResponse)
def secrets_discard(request: Request):
    secrets_store.discard()
    return secrets_store.render(request)


@router.post("/secrets/variable/add", response_class=HTMLResponse)
def secrets_var_add(request: Request):
    _vars_add(secrets_store.draft, secrets_store.default_new_name)
    return secrets_store.render(request)




# ---------------------------------------------------------------------------
# Helper: render a single procedure section HTML string
# ---------------------------------------------------------------------------

def _render_procedure_section(uuid: str, draft: Workflow, proc_name: str, ctx: dict) -> str:
    steps = draft.procedures.get(proc_name, [])
    return templates.get_template("partials/procedure_section.html").render(
        proc_name=proc_name,
        steps=steps,
        workflow_uuid=uuid,
        command_groups=ctx["command_groups"],
        command_args=ctx["command_args"],
        command_docs=ctx["command_docs"],
        var_types=ctx["var_types"],
        is_start=(proc_name == "start"),
    )


def _render_step_row(uuid: str, draft: Workflow, proc_name: str, step_idx: int, ctx: dict) -> str:
    step = draft.procedures[proc_name][step_idx]
    return templates.get_template("partials/step_row.html").render(
        step=step,
        step_idx=step_idx,
        workflow_uuid=uuid,
        proc_name=proc_name,
        command_groups=ctx["command_groups"],
        command_args=ctx["command_args"],
        command_docs=ctx["command_docs"],
        var_types=ctx["var_types"],
    )
