from typing import Any
from pydantic import BaseModel, Field


class Stat(BaseModel):
    label: str
    value: float
    percent: bool = False


class Artifact(BaseModel):
    icon: str | None = None
    slot: str
    name: str
    set_name: str
    level: int
    rarity: int
    main_stat: Stat | None = None
    substats: list[Stat] = Field(default_factory=list)
    crit_value: float = 0


class Character(BaseModel):
    id: int
    name: str
    element: str = "Unknown"
    level: int = 0
    ascension: int = 0
    friendship: int = 0
    constellation: int = 0
    talents: dict[str, int] = Field(default_factory=dict)
    icon: str | None = None
    build_available: bool = True
    weapon: dict[str, Any] | None = None
    stats: list[Stat] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
