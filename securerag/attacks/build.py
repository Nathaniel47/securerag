"""Build, save and load the 100 attack attempts (25 per attack) from the question set."""

import json
import random
from pathlib import Path

from securerag.attacks import direct_injection, indirect_injection, leakage, poisoning
from securerag.attacks.base import Attack
from securerag.config import Config

PER_ATTACK = 25
ATTACKS_PATH = Path("data/attacks.jsonl")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def build_attacks(
    questions: list[dict], restricted: list[dict], seed: int, n: int = PER_ATTACK
) -> list[Attack]:
    """Target questions are drawn without overlap: poisoning, indirect and direct injection each
    get their own n questions, so no clean question is the target of two attacks."""
    rng = random.Random(seed)
    shuffled = sorted(questions, key=lambda q: q["id"])
    rng.shuffle(shuffled)
    pool = [q["answer"] for q in questions]
    return [
        *poisoning.build(shuffled[:n], pool, n, rng),
        *indirect_injection.build(shuffled[n : 2 * n], n, rng),
        *direct_injection.build(shuffled[2 * n : 3 * n], n, rng),
        *leakage.build(restricted, n, rng),
    ]


def save_attacks(attacks: list[Attack], path: Path = ATTACKS_PATH) -> None:
    path.write_text(
        "".join(json.dumps(a.to_dict(), ensure_ascii=False) + "\n" for a in attacks),
        encoding="utf-8",
    )


def load_attacks(path: Path = ATTACKS_PATH) -> list[Attack]:
    return [Attack.from_dict(d) for d in load_jsonl(path)]


if __name__ == "__main__":
    data = Path("data")
    attacks = build_attacks(
        load_jsonl(data / "questions.jsonl"), load_jsonl(data / "restricted.jsonl"), Config().seed
    )
    save_attacks(attacks)
    kinds = {k: sum(a.kind == k for a in attacks) for k in sorted({a.kind for a in attacks})}
    print(f"{len(attacks)} attacks {kinds}")
