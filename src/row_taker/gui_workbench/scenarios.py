"""Compatibility facade for the public workbench scenario API."""

from row_taker.gui_workbench.scenario_catalog import get_scenario, scenario_names, scenarios
from row_taker.gui_workbench.scenario_types import (
    ANIMATION_FRAMES,
    DEFAULT_SIZE,
    ConnectWorkbenchScenario,
    GameWorkbenchScenario,
    LobbyWorkbenchScenario,
    ScenarioCategory,
    WorkbenchScenario,
    scenario_category,
)

__all__ = [
    "ANIMATION_FRAMES",
    "DEFAULT_SIZE",
    "ConnectWorkbenchScenario",
    "GameWorkbenchScenario",
    "LobbyWorkbenchScenario",
    "ScenarioCategory",
    "WorkbenchScenario",
    "get_scenario",
    "scenario_category",
    "scenario_names",
    "scenarios",
]
