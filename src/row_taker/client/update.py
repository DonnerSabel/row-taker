from __future__ import annotations

from dataclasses import dataclass

from row_taker.client.core_state import ClientCoreState, PendingAction
from row_taker.client.presentation_events import PresentationEvent
from row_taker.protocol.messages import ClientToServerMessage, ServerToClientMessage


@dataclass(frozen=True, slots=True)
class CoreEffect:
    """Marker base class for frontend-visible client-core effects."""


@dataclass(frozen=True, slots=True)
class EffectStateChanged(CoreEffect):
    """The core state changed in a way that usually requires a rerender."""


@dataclass(frozen=True, slots=True)
class EffectPresentationQueued(CoreEffect):
    count: int


@dataclass(frozen=True, slots=True)
class EffectPresentationAdvanced(CoreEffect):
    event: PresentationEvent


@dataclass(frozen=True, slots=True)
class EffectPendingActionChanged(CoreEffect):
    action: PendingAction


@dataclass(frozen=True, slots=True)
class EffectSessionEnded(CoreEffect):
    message: str


@dataclass(frozen=True, slots=True)
class CoreUpdate:
    """Canonical result object returned by GameClientCore.

    Frontends should treat this object as the answer of the client core.
    """

    state: ClientCoreState
    applied_server_messages: tuple[ServerToClientMessage, ...] = ()
    outbound_messages: tuple[ClientToServerMessage, ...] = ()
    local_messages: tuple[str, ...] = ()
    effects: tuple[CoreEffect, ...] = ()
