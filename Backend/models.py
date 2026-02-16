from sqlalchemy import Column, Integer, String, Float
from db import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    mood = Column(Float, default=0.0)
    current_goal = Column(String, nullable=True)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    initiator = Column(String)
