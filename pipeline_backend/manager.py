from threading import Thread, Event
from datetime import datetime,timedelta
from time import sleep
from .instances import *
from .procedure_runner import *
from .persistence import *

# TODO - loading some addons by including all sub-folders with __init__.py files in builtin_addons and user_addons

class PipelineManager(Thread):
    keep_running:bool
    something_happened:Event
    def __init__(self) -> None:
        super().__init__()
        self.keep_running = True
        self.something_happened = Event()
    def restore_state(self,filename:str="pipeline_state.json"):
        load_pipeline_global_state_from_file(filename)
    def save_state(self, filename: str = "pipeline_state.json"):
        save_pipeline_global_state_to_file(filename)

    def run_due_instances(self)->datetime|None:
        """Runs all the instances that are due to be run until they yield, and then returns the next due time."""
        current_time = datetime.now()
        next_due_time = None
        for instance in global_instances:
            if not self.keep_running:
                return next_due_time
            if instance.past_time_to_run(current_time):
                runner = ProcedureRunner(instance)
                runner.run_instance_until_yield()
            if next_due_time==None or instance.next_processing_time<next_due_time:
                next_due_time = instance.next_processing_time
        return next_due_time

    def run(self):
        while self.keep_running:
            self.something_happened.clear()
            
            next_due_time = self.run_due_instances()
            if next_due_time == None:
                self.something_happened.wait()
                continue
        
            current_time = datetime.now()
            minimum_next_due_time = current_time + timedelta(seconds=15)
            if next_due_time < minimum_next_due_time:
                next_due_time = minimum_next_due_time
            self.something_happened.wait((next_due_time-current_time).total_seconds())
    def notify_of_something_happening(self):
        self.something_happened.set()
    def stop(self):
        self.keep_running = False
        self.notify_of_something_happening()
