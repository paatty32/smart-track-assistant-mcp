from datetime import date

from pydantic import BaseModel, Field

class TrainingPlanCreate(BaseModel):
    datum: date = Field(description="Das Datum des Trainings im Format DD.MM.YYYY (z.B. 03.02.2026).")
    wetter: str = Field(description="Wetterbedingungen während des Trainings, z.B. '15 Grad, leicht bewölkt, trocken'.")
    aufwaermen: str = Field(description="Detaillierte Beschreibung des Aufwärmprogramms (Einlaufen, Lauf-ABC, Dehnen etc.).")
    hauptteil: str = Field(description="Der Kern des Trainings mit genauen Übungen, Distanzen, Wiederholungen und Pausen.")
