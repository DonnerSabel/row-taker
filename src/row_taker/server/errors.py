from __future__ import annotations


class ClientRequestRejected(ValueError):
    """An expected client request error that is safe to report to the client."""
