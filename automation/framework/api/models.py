from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any


class Selection(str, Enum):
    HOME = "HOME"
    DRAW = "DRAW"
    AWAY = "AWAY"


@dataclass(frozen=True)
class Match:
    id: str
    competition: str
    kickoff_date: date
    home_team: str
    away_team: str
    odds: dict[Selection, float]

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "Match":
        return cls(
            id=payload["id"],
            competition=payload["competition"],
            kickoff_date=date.fromisoformat(payload["kickoffDate"]),
            home_team=payload["homeTeam"],
            away_team=payload["awayTeam"],
            odds={
                Selection.HOME: payload["odds"]["home"],
                Selection.DRAW: payload["odds"]["draw"],
                Selection.AWAY: payload["odds"]["away"],
            },
        )

    @property
    def label(self) -> str:
        return f"{self.home_team} vs {self.away_team}"

    def is_upcoming(self, today: date | None = None) -> bool:
        return self.kickoff_date >= (today or date.today())
