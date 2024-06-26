from .workflows import *
from .instances import *
from .variables import *
import json

# This is the functionality to save and restore the state of the program to/from disk.
# global_workflows, global_instances, and global_variables are the state trackers that we care about

def save_pipeline_global_state() -> str:
    persistant_data = {
        "workflows": {uuid:w.json_savable() for uuid,w in global_workflows.items()},
        "instances": {uuid:i.json_savable() for uuid,i in global_instances.items()},
        "variables": {name:v.json_savable() for name,v in global_variables.items()}
    }
    return json.dumps(persistant_data,indent=4)

def save_pipeline_global_state_to_file(filepath: str) -> None:
    s = save_pipeline_global_state()
    f = open(filepath,"w")
    f.write(s)
    f.close()


def load_pipeline_global_state(state:str) -> None:
    persistant_data = json.loads(state)

    global_workflows.clear()
    for uuid,workflow_data in persistant_data["workflows"].items():
        workflow = Workflow()
        workflow.json_loadable(workflow_data)
        global_workflows[uuid]=workflow
    
    global_instances.clear()
    for uuid,instance_data in persistant_data["instances"].items():
        instance = Instance()
        instance.json_loadable(instance_data)
        global_instances[uuid]=instance
    
    global_variables.clear()
    for var_name,var_data in persistant_data["variables"].items():
        var = WorkVariable()
        var.json_loadable(var_data)
        global_variables[var_name] = var

def load_pipeline_global_state_from_file(filepath: str) -> None:
    try:
        f = open(filepath,"r")
    except FileNotFoundError:
        print(f"Unable to open filepath {filepath} - skipping restoring state")
        return
    load_pipeline_global_state(f.read())
    f.close()
