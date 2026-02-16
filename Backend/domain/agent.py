import random


class Agent:
    def __init__(self, id: int, name: str, world):
        self.id = id
        self.name = name
        self.world = world

        self.emotion = {"valence": 0.0, "arousal": 0.0}
        self.state = "idle"

    def decide_target(self):
        free_agents = [
            a for a in self.world.agents.values()
            if a.id != self.id and a.state == "idle"
        ]
        target = random.choice(free_agents) if free_agents else None
        if target:
            print(f"[Agent] {self.name} wants to talk to {target.name}")
        return target

    def generate_reply(self, context=None):
        tone = random.choice(["positive", "neutral", "negative"])
        return "msg", tone

    def apply_emotion_delta(self, delta):
        self.emotion["valence"] += delta.get("valence", 0)
        self.emotion["arousal"] += delta.get("arousal", 0)