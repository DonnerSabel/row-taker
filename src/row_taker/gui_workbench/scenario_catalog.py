from __future__ import annotations

from row_taker.gui_workbench.connect_scenarios import CONNECT_SCENARIO_FACTORIES
from row_taker.gui_workbench.game_scenarios import GAME_SCENARIO_FACTORIES
from row_taker.gui_workbench.lobby_scenarios import LOBBY_SCENARIO_FACTORIES
from row_taker.gui_workbench.scenario_types import (
    ScenarioCategory,
    ScenarioFactory,
    WorkbenchScenario,
)

_SCENARIO_FACTORIES: dict[ScenarioCategory, dict[str, ScenarioFactory]] = {
    "connect": CONNECT_SCENARIO_FACTORIES,
    "lobby": LOBBY_SCENARIO_FACTORIES,
    "game": GAME_SCENARIO_FACTORIES,
}


def scenario_names(category: ScenarioCategory | None = None) -> tuple[str, ...]:
    if category is not None:
        return tuple(_SCENARIO_FACTORIES[category])
    return tuple(name for factories in _SCENARIO_FACTORIES.values() for name in factories)


def get_scenario(name: str) -> WorkbenchScenario:
    for factories in _SCENARIO_FACTORIES.values():
        factory = factories.get(name)
        if factory is not None:
            return factory()
    available = ", ".join(scenario_names())
    raise KeyError(f"unknown workbench scenario {name!r}; available: {available}")


def scenarios(category: ScenarioCategory | None = None) -> tuple[WorkbenchScenario, ...]:
    categories = (
        _SCENARIO_FACTORIES if category is None else {category: _SCENARIO_FACTORIES[category]}
    )
    return tuple(factory() for factories in categories.values() for factory in factories.values())
