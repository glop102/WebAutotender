from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .workflows import Workflow
    from .instances import Instance
    from .variables import WorkVariable


class PipelineContext:
    workflows: dict[str, Workflow]
    instances: dict[str, Instance]
    variables: dict[str, WorkVariable]
    secrets: dict[str, WorkVariable]

    def __init__(self) -> None:
        self.workflows = {}
        self.instances = {}
        self.variables = {}
        self.secrets = {}
