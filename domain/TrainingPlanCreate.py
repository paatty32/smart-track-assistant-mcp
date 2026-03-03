from datetime import date

from pydantic import BaseModel


class TrainingPlanCreate(BaseModel):
    datum: date
    wetter: str
    aufwaermen: str
    hauptteil: str
