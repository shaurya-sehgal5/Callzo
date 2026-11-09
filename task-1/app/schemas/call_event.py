from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CallEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=100)
    event_type: Literal[
        "call.started",
        "call.ended",
        "call.failed",
    ]

    account_id: str = Field(min_length=1, max_length=50)
    call_id: str = Field(min_length=1, max_length=100)

    timestamp: datetime

    duration_seconds: int = Field(strict=True, ge=0)
    cost_cents: int = Field(strict=True, ge=0)

    destination_country: str = Field(min_length=2, max_length=5)

    def validate_event_consistency(self) -> None:
        if self.event_type in ("call.started", "call.failed"):
            if self.duration_seconds != 0 or self.cost_cents != 0:
                raise ValueError(
                    "Started and failed events must have zero duration and cost"
                )

        if self.event_type == "call.ended":
            if self.duration_seconds <= 0:
                raise ValueError(
                    "Ended events must have a positive duration"
                )