import random


class Dialogue:
    def __init__(self, agent_a, agent_b):
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.remaining_ticks = random.randint(1, 3)
        self.messages = []
        self.tone_score = 0  # накопительный тон (-, 0, +)

    def tick(self):
        self.remaining_ticks -= 1

    def is_finished(self):
        return self.remaining_ticks <= 0