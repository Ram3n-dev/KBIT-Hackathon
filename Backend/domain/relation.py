class Relation:
    def __init__(self, source_id: int, target_id: int):
        self.source_id = source_id
        self.target_id = target_id
        self.sympathy = 0.0
        self.trust = 0.0

    def apply_delta(self, sympathy_delta: float, trust_delta: float):
        self.sympathy += sympathy_delta
        self.trust += trust_delta