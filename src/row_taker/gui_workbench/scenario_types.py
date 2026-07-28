from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from row_taker.client.state import ClientState
from row_taker.gui.connect_form_state import ConnectFormState

DEFAULT_SIZE = (1600, 900)
ANIMATION_FRAMES = (0, 8, 16, 24, 32)
ScenarioCategory = Literal["connect", "lobby", "game"]


@dataclass(frozen=True, slots=True)
class ConnectWorkbenchScenario:
    """Deterministic input fixture for the production ``ConnectFrame``."""

    name: str
    description: str
    connect_form: ConnectFormState
    default_size: tuple[int, int] = DEFAULT_SIZE
    interesting_frames: tuple[int, ...] = (0,)


@dataclass(frozen=True, slots=True)
class LobbyWorkbenchScenario:
    """Deterministic input fixture for the production ``LobbyFrame``."""

    name: str
    description: str
    state: ClientState
    default_size: tuple[int, int] = DEFAULT_SIZE
    interesting_frames: tuple[int, ...] = (0,)


@dataclass(frozen=True, slots=True)
class GameWorkbenchScenario:
    """Deterministic input fixture for the production ``GameFrame``.

    The scenario owns no rendering information. It only supplies the same
    ``ClientState`` and timing inputs that the live GUI passes to ``GameFrame``.
    """

    name: str
    description: str
    state: ClientState
    default_size: tuple[int, int] = DEFAULT_SIZE
    interesting_frames: tuple[int, ...] = (0,)


WorkbenchScenario = ConnectWorkbenchScenario | LobbyWorkbenchScenario | GameWorkbenchScenario
ScenarioFactory = Callable[[], WorkbenchScenario]


def scenario_category(scenario: WorkbenchScenario) -> ScenarioCategory:
    match scenario:
        case ConnectWorkbenchScenario():
            return "connect"
        case LobbyWorkbenchScenario():
            return "lobby"
        case GameWorkbenchScenario():
            return "game"
