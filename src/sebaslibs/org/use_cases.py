"""Use cases: orchestrates planning and execution."""

from __future__ import annotations

from pathlib import Path

from ..core.entities import Plan
from .executor import Executor
from .planner import Planner
from .rule_engine import RuleEngine


class PlanUseCase:
    def __init__(
        self,
        source: Path,
        destination: Path,
        max_per_folder: int = 500,
        rules_path: Path | None = None,
    ) -> None:
        self.source = source
        self.destination = destination
        self.max_per_folder = max_per_folder
        self.rules_path = rules_path

    def execute(self) -> Plan:
        rules = RuleEngine(self.rules_path) if self.rules_path else None
        planner = Planner(
            source=self.source,
            destination=self.destination,
            max_per_folder=self.max_per_folder,
            rules_engine=rules,
        )
        return planner.scan()


class ExecuteUseCase:
    def __init__(
        self,
        plan: Plan,
        simulate: bool = False,
        resume: bool = False,
        hard_delete: bool = False,
    ) -> None:
        self.plan = plan
        self.simulate = simulate
        self.resume = resume
        self.hard_delete = hard_delete

    def execute(self) -> list:
        executor = Executor(
            plan=self.plan,
            simulate=self.simulate,
            resume=self.resume,
            hard_delete=self.hard_delete,
        )
        return executor.run()
