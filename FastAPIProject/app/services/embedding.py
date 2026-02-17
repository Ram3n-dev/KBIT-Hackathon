import hashlib
import math
import re

from app.config import get_settings


settings = get_settings()
TOKEN_RE = re.compile(r"[a-zA-Zа-яА-Я0-9_]+", flags=re.UNICODE)


def embed_text(text: str) -> list[float]:
    dim = settings.memory_embedding_dim
    vec = [0.0] * dim
    tokens = TOKEN_RE.findall(text.lower())
    if not tokens:
        return vec

    for token in tokens:
        h = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "big") % dim
        sign = 1.0 if (h[4] % 2 == 0) else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]
