# domain/user.py

from world import World


class User:
    def __init__(self, user_id: int, username: str):
        self.id = user_id
        self.username = username
        self.world = World(owner_id=user_id)

    def create_world(self):
        self.world = World(owner_id=self.id)

    def get_world(self) -> World:
        return self.world
