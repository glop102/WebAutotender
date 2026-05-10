import pytest
import pipeline_backend  # registers all builtin commands as a side effect
from pipeline_backend.manager import PipelineManager


@pytest.fixture
def mgr():
    """A fresh PipelineManager (and thus a fresh PipelineContext) per test."""
    return PipelineManager()
