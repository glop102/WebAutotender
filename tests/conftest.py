import pytest
import pipeline_backend  # registers all builtin commands as a side effect
from pipeline_backend.manager import pipelineManager


@pytest.fixture(autouse=True)
def clean_global_state():
    pipelineManager.ctx.instances.clear()
    pipelineManager.ctx.workflows.clear()
    pipelineManager.ctx.variables.clear()
    pipelineManager.ctx.secrets.clear()
    yield
    pipelineManager.ctx.instances.clear()
    pipelineManager.ctx.workflows.clear()
    pipelineManager.ctx.variables.clear()
    pipelineManager.ctx.secrets.clear()
