from datetime import date
from typing import Optional

from sqlmodel import SQLModel, Field


class TrainingPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    datum: date
    wetter: str
    aufwaermen: str
    hauptteil: str
    fingerprint: str = Field(unique=True, nullable=False)

