from asyncio import Handle, TimerHandle, get_running_loop, gather
from datetime import datetime, timedelta
import importlib.util
import json
import pathlib

from .context import PipelineContext
from .workflows import Workflow
from .instances import Instance
from .variables import WorkVariable
from .procedure_runner import ProcedureRunner
from .event_callbacks import eventsCallbackManager, EventCallbacksManager


class PipelineManager:
    ctx: PipelineContext
    delayedTask: Handle | TimerHandle | None
    __backing_store_filename: str
    __secrets_filename: str

    def __init__(self) -> None:
        super().__init__()
        self.ctx = PipelineContext()
        self.delayedTask = None
        self.__backing_store_filename = ""
        self.__secrets_filename = ""

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_state(self, filename: str = "") -> None:
        target = filename or self.__backing_store_filename or "pipeline_state.json"
        data = {
            "workflows": {uuid: w.json_savable() for uuid, w in self.ctx.workflows.items()},
            "instances": {uuid: i.json_savable() for uuid, i in self.ctx.instances.items()},
            "variables": {name: v.json_savable() for name, v in self.ctx.variables.items()},
        }
        with open(target, "w") as f:
            f.write(json.dumps(data, indent=4))

    def restore_state(self, filename: str = "pipeline_state.json") -> None:
        self.__backing_store_filename = filename
        try:
            with open(filename, "r") as f:
                data = json.loads(f.read())
        except FileNotFoundError:
            print(f"Unable to open filepath {filename} - skipping restoring state")
            return

        self.ctx.workflows.clear()
        for uuid, workflow_data in data["workflows"].items():
            workflow = Workflow(self.ctx)
            workflow.json_loadable(workflow_data)
            self.ctx.workflows[uuid] = workflow

        self.ctx.instances.clear()
        for uuid, instance_data in data["instances"].items():
            instance = Instance(self.ctx)
            instance.json_loadable(instance_data)
            self.ctx.instances[uuid] = instance

        self.ctx.variables.clear()
        for var_name, var_data in data["variables"].items():
            var = WorkVariable()
            var.json_loadable(var_data)
            self.ctx.variables[var_name] = var

    def save_secrets(self, filename: str = "") -> None:
        target = filename or self.__secrets_filename or "secrets.json"
        data = {name: v.json_savable() for name, v in self.ctx.secrets.items()}
        with open(target, "w") as f:
            f.write(json.dumps(data, indent=4))

    def restore_secrets(self, filename: str = "secrets.json") -> None:
        self.__secrets_filename = filename
        try:
            with open(filename, "r") as f:
                data = json.loads(f.read())
        except FileNotFoundError:
            print(f"Unable to open secrets file {filename} - skipping restoring secrets")
            return

        self.ctx.secrets.clear()
        for var_name, var_data in data.items():
            var = WorkVariable()
            var.json_loadable(var_data)
            self.ctx.secrets[var_name] = var

    # ── Scheduling ────────────────────────────────────────────────────────────

    async def run_due_instances(self) -> None:
        """Runs all the instances that are due to be run until they yield."""
        current_time = datetime.now()
        due_instances = [i for i in self.ctx.instances.values()
                         if i.is_allowed_to_run() and i.past_time_to_run(current_time)]

        async def run_one(instance):
            runner = ProcedureRunner(instance)
            await runner.run_instance_until_yield()
            await eventsCallbackManager.signal_event(
                EventCallbacksManager.Events.RefreshInstance,
                instance.uuid
            )

        await gather(*[run_one(i) for i in due_instances])
        if len(due_instances) > 0:
            self.save_state()

    def get_next_due_time(self) -> datetime | None:
        current_time = datetime.now()
        next_due_time = current_time
        minimum_next_due_time = current_time + timedelta(seconds=1)

        possible_instances = [i for i in self.ctx.instances.values()
                              if i.is_allowed_to_run()]
        if len(possible_instances) == 0:
            return None
        for instance in possible_instances:
            next_due_time = min(next_due_time, instance.next_processing_time)
        return max(next_due_time, minimum_next_due_time)

    async def run(self):
        await self.run_due_instances()
        next_due_time = self.get_next_due_time()
        if next_due_time:
            next_due_time = (next_due_time - datetime.now()).total_seconds()
            self.delayedTask = get_running_loop().call_later(
                next_due_time,
                lambda: get_running_loop().create_task(self.run())
            )

    async def notify_of_something_happening(self):
        # Cancel the callback to run() and instead call run() asap
        if self.delayedTask:
            self.delayedTask.cancel()
        self.delayedTask = get_running_loop().call_soon(lambda: get_running_loop().create_task(self.run()))

    async def start(self):
        await self.notify_of_something_happening()

    async def stop(self):
        if self.delayedTask:
            self.delayedTask.cancel()

    def import_addons_from_folder(self, foldername: str) -> list:
        """This will attempt to import all the folders in a folder in the assumption they are modules. This will let them run naturally and do things like register commands. It will return a list of these sucessfully imported modules."""
        modules_parent = pathlib.Path(foldername)
        if not modules_parent.exists():
            print(f"Unable to find the location {foldername}")
            return []
        succesful_modules = []
        for module_path in modules_parent.iterdir():
            if not module_path.is_dir():
                continue
            try:
                spec = importlib.util.spec_from_file_location("module.name", module_path.as_posix() + "/__init__.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as e:
                import traceback
                print(traceback.format_exc())
                continue
            succesful_modules.append(module)
        return succesful_modules


pipelineManager = PipelineManager()
