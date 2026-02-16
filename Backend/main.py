import logging
import uvicorn
from fastapi import FastAPI
from db import engine
from models import Base
from sqlalchemy.orm import Session
from fastapi import Depends
from db import SessionLocal
from models import Agent, Event
import asyncio
import random
from agent_iteration import agent_interaction
app = FastAPI()

Base.metadata.create_all(bind=engine)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

# флаги на состояния

simulation_task = None
simulation_running = False


#endpoint
@app.get("/")
def root():
    return {"status": "world alive"}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/agents")
def create_agent(name: str, db: Session = Depends(get_db)):
    agent = Agent(name=name)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@app.get("/agents")
def list_agents(db: Session = Depends(get_db)):
    return db.query(Agent).all()


@app.get("/events")
def get_events(db: Session = Depends(get_db)):
    return db.query(Event).all()

async def simulation_loop():
    global simulation_running

    logger.info("Simulation loop started")

    while simulation_running:
        try:
            db = SessionLocal()
            agents = db.query(Agent).all()

            agent_interaction(db, agents)

            logger.info(f"Tick: {len(agents)} agents")

            for agent in agents:
                delta = random.uniform(-0.2, 0.2)
                agent.mood += delta

                logger.info(f"{agent.name} mood -> {round(agent.mood,2)}")

            db.commit()
            db.close()

        except Exception as e:
            logger.exception("Simulation crashed")

        await asyncio.sleep(5)

    logger.info("Simulation loop stopped")

@app.post("/simulation/start")
async def start_simulation():
    global simulation_task, simulation_running

    if simulation_running:
        return {"status": "already running"}

    simulation_running = True
    simulation_task = asyncio.create_task(simulation_loop())

    return {"status": "started"}

@app.post("/simulation/stop")
async def stop_simulation():
    global simulation_running

    simulation_running = False

    return {"status": "stopped"}


@app.on_event("startup")
async def start_simulation():
    asyncio.create_task(simulation_loop())
if __name__ == "__main__":
    uvicorn.run('main:app', host="0.0.0.0", port=8000, reload=True)