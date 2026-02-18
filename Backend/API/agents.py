# API/agents.py
from fastapi import APIRouter
from services.user_service import UserService

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("/")
def get_agents():
    return UserService().get_all_agents()

@router.post("/")
def create_agent(data: dict):
    return UserService().create_agent(data)
