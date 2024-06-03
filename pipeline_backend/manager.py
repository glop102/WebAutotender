from threading import Thread, Event
from datetime import datetime,timedelta
from time import sleep
import importlib.util
import pathlib
from .instances import *
from .procedure_runner import *
from .persistence import *

# TODO - Add in callbacks for certain events to enable things like websockets giving useful information

class PipelineManager(Thread):
    keep_running:bool
    something_happened: Event = Event() # Shared event to simplify the notify scheme
    def __init__(self) -> None:
        super().__init__()
        self.keep_running = True
    def restore_state(self,filename:str="pipeline_state.json"):
        load_pipeline_global_state_from_file(filename)
    def save_state(self, filename: str = "pipeline_state.json"):
        save_pipeline_global_state_to_file(filename)

    def run_due_instances(self)->None:
        """Runs all the instances that are due to be run until they yield."""
        current_time = datetime.now()
        due_instances = [i for i in global_instances 
                         if i.is_allowed_to_run() and i.past_time_to_run(current_time)]
        for instance in due_instances:
            if not self.keep_running:
                return
            runner = ProcedureRunner(instance)
            runner.run_instance_until_yield()

    def get_next_due_time(self)->datetime:
        current_time = datetime.now()
        next_due_time = current_time
        minimum_next_due_time = current_time + timedelta(seconds=1)

        due_instances = [i for i in global_instances
                         if i.is_allowed_to_run()]
        for instance in due_instances:
            next_due_time = min(next_due_time,instance.next_processing_time)
        return max(next_due_time,minimum_next_due_time)

    def run(self):
        while self.keep_running:
            self.something_happened.clear()
            
            self.run_due_instances()
            if len(global_instances) == 0:
                self.something_happened.wait()
            else:
                next_due_time = self.get_next_due_time()
                self.something_happened.wait((next_due_time-datetime.now()).total_seconds())
    @classmethod
    def notify_of_something_happening(cls):
        cls.something_happened.set()
    def stop(self):
        self.keep_running = False
        self.notify_of_something_happening()

    @classmethod
    def import_addons_from_folder(cls,foldername:str) -> list:
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
