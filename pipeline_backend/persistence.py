from .workflows import *
from .instances import *
from .variables import *
import json

# This is the functionality to save and restore the state of the program to/from disk.
# global_workflows, global_instances, and global_variables are the state trackers that we care about

def save_pipeline_global_state() -> str:
    persistant_data = {
        "workflows": [w.json_savable() for w in global_workflows.values()],
        "instances": [i.json_savable() for i in global_instances.values()],
        "variables": {}
    }
    for var_name in global_variables:
        persistant_data["variables"][var_name] = global_variables[var_name].json_savable()
    return json.dumps(persistant_data,indent=4)

def save_pipeline_global_state_to_file(filepath: str) -> None:
    s = save_pipeline_global_state()
    f = open(filepath,"w")
    f.write(s)
    f.close()


def load_pipeline_global_state(state:str) -> None:
    persistant_data = json.loads(state)

    global_workflows.clear()
    for workflow_data in persistant_data["workflows"]:
        workflow = Workflow()
        workflow.json_loadable(workflow_data)
        global_workflows[workflow.name]=workflow
    
    global_instances.clear()
    for instance_data in persistant_data["instances"]:
        instance = Instance()
        instance.json_loadable(instance_data)
        global_instances[instance.uuid]=instance
    
    global_variables.clear()
    for var_name in persistant_data["variables"]:
        var = WorkVariable()
        var.json_loadable(persistant_data["variables"][var_name])
        global_variables[var_name] = var

def load_pipeline_global_state_from_file(filepath: str) -> None:
    try:
        f = open(filepath,"r")
    except FileNotFoundError:
        print(f"Unable to open filepath {filepath} - skipping restoring state")
        return
    load_pipeline_global_state(f.read())
    f.close()
