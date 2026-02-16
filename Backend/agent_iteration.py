import random

from models import Event
import logging


logger = logging.getLogger(__name__)

PHRASES = [
    {"text": "Привет!", "emotion": 0.1},
    {"text": "Ты сегодня молодец", "emotion": 0.3},
    {"text": "Отстань", "emotion": -0.3},
    {"text": "Ты меня раздражаешь", "emotion": -0.5},
    {"text": "Давай дружить", "emotion": 0.4},
    {"text": "Мне всё равно", "emotion": -0.1},
]

def agent_interaction(db, agents):
    if len(agents) < 2:
        logger.info("Not enough agents for interaction")
        return

    a1, a2 = random.sample(agents, 2)
    phrase = random.choice(PHRASES)

    old_mood = a2.mood
    a2.mood += phrase["emotion"]

    logger.info(
        f"{a1.name} -> {a2.name}: '{phrase['text']}' "
        f"(mood {round(old_mood,2)} -> {round(a2.mood,2)})"
    )

    event = Event(
        content=f"{a1.name} -> {a2.name}: {phrase['text']}",
        initiator="agent"
    )

    db.add(event)

