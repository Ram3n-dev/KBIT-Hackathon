import random
from typing import Dict, Tuple, List

from agent import Agent
from dialogue import Dialogue
from event import Event
from relation import Relation


class World:
    def __init__(self):
        self.agents: Dict[int, Agent] = {}
        self.relations: Dict[Tuple[int, int], Relation] = {}
        self.active_dialogues: List[Dialogue] = []
        self.events: List[Event] = []
        self.current_tick = 0

    # ----- relations -----

    def get_relation(self, source_id, target_id):
        key = (source_id, target_id)
        if key not in self.relations:
            self.relations[key] = Relation(source_id, target_id)
        return self.relations[key]

    # ----- dialogue management -----

    def start_dialogue(self, a: Agent, b: Agent):
        print(f"[World] Dialogue started: {a.name} <-> {b.name}")
        d = Dialogue(a, b)
        a.state = "talking"
        b.state = "talking"
        self.active_dialogues.append(d)

    def finish_dialogue(self, dialogue: Dialogue):
        a, b = dialogue.agent_a, dialogue.agent_b
        print(f"[World] Dialogue finished: {a.name} <-> {b.name}")

        rel_ab = self.get_relation(a.id, b.id)
        rel_ab.apply_delta(dialogue.tone_score * 0.1, 0.05)

        a.state = "idle"
        b.state = "idle"

        self.active_dialogues.remove(dialogue)

    # ----- user intervention -----

    def inject_message(self, agent_id, target_id, content):
        ev = Event(agent_id, target_id, content)
        self.events.append(ev)

    # ----- tick -----

    def tick(self):
        self.current_tick += 1

        def tick(self):
            print(f"[Dialogue] {self.agent_a.name} talking with {self.agent_b.name} "
                  f"(remaining {self.remaining_ticks})")
            self.remaining_ticks -= 1

        # обновление диалогов
        for d in self.active_dialogues[:]:
            d.tick()
            if d.is_finished():
                self.finish_dialogue(d)

        # свободные агенты инициируют разговор
        free_agents = [a for a in self.agents.values() if a.state == "idle"]
        random.shuffle(free_agents)

        for agent in free_agents:
            if agent.state != "idle":
                continue
            target = agent.decide_target()
            if target:
                self.start_dialogue(agent, target)

    # ----- graph export -----

    def export_graph(self):
        nodes = [
            {
                "id": a.id,
                "state": a.state,
                "emotion": a.emotion
            }
            for a in self.agents.values()
        ]

        edges = [
            {
                "source": r.source_id,
                "target": r.target_id,
                "sympathy": r.sympathy
            }
            for r in self.relations.values()
        ]

        active_edges = [
            (d.agent_a.id, d.agent_b.id)
            for d in self.active_dialogues
        ]

        return nodes, edges, active_edges


# ---------- example ----------

world = World()

world.agents[1] = Agent(1, "Slime1", world)
world.agents[2] = Agent(2, "Slime2", world)
world.agents[3] = Agent(3, "Slime3", world)

for _ in range(50):
    world.tick()