import logging
from datetime import date

import httpx
from mcp.server import FastMCP
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from domain.TrainingPlan import TrainingPlan
from domain.TrainingPlanCreate import TrainingPlanCreate
from domain.db_utils import plan_fingerprint

URL = "https://api.open-meteo.com/v1/forecast"
params = {
    #Düsseldorf
	"latitude": 51.2217,
	"longitude": 6.7762,
	"daily": ["temperature_2m_max", "temperature_2m_min", "rain_sum", "snowfall_sum", "wind_speed_10m_max"],
	"hourly": ["temperature_2m", "rain", "showers", "wind_speed_10m"],
	"models": "icon_seamless",
	"timezone": "Europe/Berlin",
}

DATABASE_URL = "postgresql+asyncpg://user:password@db:5432/smartAssistantDb"

enginne = create_async_engine(DATABASE_URL, echo=True)

#Async Session Factory
async_session = async_sessionmaker(enginne, class_=AsyncSession, expire_on_commit=False)

weather_mcp = FastMCP("weather", host="0.0.0.0", port=8000)

logger = logging.getLogger(__name__)

def getWeather():
    response = httpx.get(URL, params=params)
    return response.text

async def insert_training_plan(session: AsyncSession, training_plan: TrainingPlanCreate, fingerprint: str):
    plan = TrainingPlan(**training_plan.model_dump(), fingerprint=fingerprint)
    logger.info(f"Plan to add {plan}")
    session.add(plan)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(select(TrainingPlan).where(TrainingPlan.fingerprint == fingerprint))
        return {
            "status": "already_exists",
            "id": existing.id
        }
    logger.info(f"End inserting training plan {training_plan}")
    await session.refresh(plan)
    return {
        "id": plan.id,
        "status": "created",
    }


async def create_training_plan(
        datum: date,
        wetter: str,
        aufwaermen: str,
        hauptteil: str,
) -> dict:
    logger.info(f"Start creating training plan {datum}, {wetter}, {aufwaermen}, {hauptteil}")
    plan = TrainingPlanCreate(
        datum=datum,
        wetter=wetter,
        aufwaermen=aufwaermen,
        hauptteil=hauptteil,
    )
    logger.info(f"Plan erstellt {plan}")
    logger.info(f"Plan model dump {plan.model_dump()}")
    return plan.model_dump()

#TODO: tool bennen
@weather_mcp.tool()
def getWeatherTool():
    return getWeather()

@weather_mcp.tool()
async def createTrainingPlan(datum: date,
        wetter: str,
        aufwaermen: str,
        hauptteil: str):

    return await create_training_plan(
        datum=datum,
        wetter=wetter,
        aufwaermen=aufwaermen,
        hauptteil=hauptteil,)

@weather_mcp.tool(name="insertTrainingPlan")
async def insertTrainingPlan( datum: date,
                              wetter: str,
                              aufwaermen: str,
                              hauptteil: str):
    logger.info(f"Start inserting training plan Datum: {datum}, Wetter: {wetter}, aufwaermen: {aufwaermen},hauptteil: {hauptteil}")
    training_plan = TrainingPlanCreate(datum=datum, wetter=wetter, aufwaermen=aufwaermen, hauptteil=hauptteil)

    logger.info(f"Plan erstellt {training_plan}")

    fingerprint = plan_fingerprint(training_plan)

    async with async_session() as session:
        try:
            existing = await session.scalar(
                select(TrainingPlan).where(
                    TrainingPlan.fingerprint == fingerprint
                )
            )

            if existing:
                return {
                    "status": "already_exists",
                    "id": existing.id
                }

            logger.info(f"Start inserting training plan {training_plan}")
            return await insert_training_plan(session, training_plan, fingerprint)
        except Exception:
            await session.rollback()
            raise

def main():
    weather_mcp.run(transport="streamable-http")
if __name__ == "__main__":
    main()