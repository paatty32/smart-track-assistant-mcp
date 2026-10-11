import asyncio
import logging
from datetime import date

import httpx
from mcp.server import FastMCP
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel

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

engine = create_async_engine(DATABASE_URL, echo=True)
#Async Session Factory
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

training_mcp = FastMCP("training_plan", host="0.0.0.0", port=8000)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def getWeather():
    response = httpx.get(URL, params=params)
    return response.text

async def create_db_and_tables_with_retry(max_retries=10, delay=2):
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
                logger.info("Tabellen erfolgreich erstellt!")
            return
        except Exception as e:
            logger.warning(f"Verbindung zur DB fehlgeschlagen, Versuch {attempt+1}/{max_retries}. Grund: {e}")
            await asyncio.sleep(delay)
    raise Exception("Konnte keine Verbindung zur Datenbank herstellen.")

async def set_up_database():
    await create_db_and_tables_with_retry()
    await engine.dispose()

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

@training_mcp.tool(
    name="get_weather_data",
    description="Holt die Wetter Daten für einen angegebenen Ort anhand"
)
def getWeatherTool():
    return getWeather()

@training_mcp.tool(
    name="create_plan",
    description="Erstellt einen Trainingsplan mit den gegebenen Informationen"
)
async def createTrainingPlan(
        datum: date,
        wetter: str,
        aufwaermen: str,
        hauptteil: str
):

    return await create_training_plan(
        datum=datum,
        wetter=wetter,
        aufwaermen=aufwaermen,
        hauptteil=hauptteil,)

@training_mcp.tool(
    name="insert_plan",
    description="Fügt einen Trainingsplan in die Datenbank ein mit einem einzigartigen Fingerprint")
async def insertTrainingPlan(plan: TrainingPlanCreate):
    logger.info(f"Start inserting training plan Datum: {plan.datum}, Wetter: {plan.wetter}, aufwaermen: {plan.aufwaermen},hauptteil: {plan.hauptteil}")
    training_plan = plan

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
    #Tabelle erstellen
    asyncio.run(set_up_database())

    training_mcp.run(transport="streamable-http")
if __name__ == "__main__":
    main()