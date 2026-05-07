import pytest
import pipeline_backend  # registers all builtin commands as a side effect
from pipeline_backend.instances import global_instances
from pipeline_backend.workflows import global_workflows
from pipeline_backend.variables import global_variables, global_secrets


@pytest.fixture(autouse=True)
def clean_global_state():
    global_instances.clear()
    global_workflows.clear()
    global_variables.clear()
    global_secrets.clear()
    yield
    global_instances.clear()
    global_workflows.clear()
    global_variables.clear()
    global_secrets.clear()
