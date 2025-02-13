from asyncio import Handle, TimerHandle, get_running_loop
from datetime import datetime,timedelta
from time import sleep
import importlib.util
import pathlib
from .instances import *
from .procedure_runner import *
from .persistence import *
from .event_callbacks import *

class PipelineManager:
    delayedTask : Handle | TimerHandle | None
    __backing_store_filename : str # the filename used to restore the state of the pipeline to let us save back to
    def __init__(self) -> None:
        super().__init__()
        self.delayedTask = None
        self.__backing_store_filename = ""
    def restore_state(self,filename:str="pipeline_state.json"):
        self.__backing_store_filename = filename
        load_pipeline_global_state_from_file(filename)
    def save_state(self, filename: str = "pipeline_state.json"):
        save_pipeline_global_state_to_file(filename)

    async def run_due_instances(self)->None:
        """Runs all the instances that are due to be run until they yield."""
        current_time = datetime.now()
        due_instances = [i for i in global_instances.values() 
                         if i.is_allowed_to_run() and i.past_time_to_run(current_time)]
        for instance in due_instances:
            runner = ProcedureRunner(instance)
            await runner.run_instance_until_yield()
            await eventsCallbackManager.signal_event(
                EventCallbacksManager.Events.RefreshInstance,
                instance.uuid
                )
        if len(due_instances) > 0:
            self.save_state(self.__backing_store_filename)

    def get_next_due_time(self)->datetime|None:
        current_time = datetime.now()
        next_due_time = current_time
        minimum_next_due_time = current_time + timedelta(seconds=1)

        possible_instances = [i for i in global_instances.values()
                         if i.is_allowed_to_run()]
        if len(possible_instances) == 0:
            return None
        for instance in possible_instances:
            next_due_time = min(next_due_time,instance.next_processing_time)
        return max(next_due_time,minimum_next_due_time)

    async def run(self):
        await self.run_due_instances()
        next_due_time = self.get_next_due_time()
        if next_due_time:
            next_due_time = (next_due_time-datetime.now()).total_seconds()
            self.delayedTask = get_running_loop().call_later(
                next_due_time,
                lambda: get_running_loop().create_task(self.run())
            )
    async def notify_of_something_happening(self):
        # Cancel the callback to run() and instead call run() asap
        if self.delayedTask:
            self.delayedTask.cancel()
        self.delayedTask = get_running_loop().call_soon( lambda: get_running_loop().create_task(self.run()) )
    async def start(self):
        await self.notify_of_something_happening()
    async def stop(self):
        if self.delayedTask:
            self.delayedTask.cancel()

    def import_addons_from_folder(self,foldername:str) -> list:
        """This will attempt to import all the folders in a folder in the assumption they are modules. This will let them run naturally and do things like register commands. It will return a list of these sucessfully imported modules."""
        modules_parent = pathlib.Path(foldername)
        if not modules_parent.exists():
            print(f"Unable to find the location {foldername}")
            return []
        succesful_modules = []
        for module_path in modules_parent.iterdir():
            if not module_path.is_dir(): continue
            try:
                spec = importlib.util.spec_from_file_location("module.name", module_path.as_posix()+"/__init__.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as e:
                print(traceback.format_exc())
                continue
            succesful_modules.append(module)
        return succesful_modules


pipelineManager = PipelineManager()