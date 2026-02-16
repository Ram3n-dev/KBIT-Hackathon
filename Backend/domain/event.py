class Event:
    def __init__(self, agent_id: int, target_id: int, content: str):
        self.agent_id = agent_id
        self.target_id = target_id
        self.content = content