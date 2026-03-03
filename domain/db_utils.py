import hashlib

from .TrainingPlanCreate import TrainingPlanCreate


def plan_fingerprint(plan: TrainingPlanCreate) -> str:
    raw = (
        f"{plan.datum}|"
        f"{plan.wetter}|"
        f"{plan.aufwaermen}|"
        f"{plan.hauptteil}"
    )

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()