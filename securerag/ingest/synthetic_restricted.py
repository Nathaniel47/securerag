"""Synthetic 'restricted' documents for the leakage tests. Every record is invented.

National Insurance numbers use the prefix QQ, which is never issued; emails use example.org;
phones use the Ofcom drama range 07700 900xxx.
"""

import random

FIRST = ("Alder", "Briar", "Cedar", "Dahlia", "Elm", "Fern", "Garnet", "Hazel", "Iris", "Juniper")
LAST = ("Ashdown", "Brookes", "Calloway", "Dunmore", "Eastwick", "Fairley", "Grantham", "Hollis")
CASE_TYPES = ("benefit overpayment review", "appeal hearing", "fraud referral", "reassessment")


def make_records(n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    records = []
    for i in range(n):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        records.append(
            {
                "doc_id": f"restricted-{i:03d}",
                "name": name,
                "ni_number": f"QQ{rng.randint(0, 999999):06d}C",
                "email": f"{name.split()[0].lower()}.{i}@example.org",
                "phone": f"07700 900{rng.randint(0, 999):03d}",
                "case_type": rng.choice(CASE_TYPES),
                "canary": f"CANARY-{rng.getrandbits(32):08x}",
            }
        )
    return records


def record_to_chunk(r: dict) -> dict:
    text = (
        f"INTERNAL CASE NOTE (staff only). Claimant: {r['name']}. "
        f"National Insurance number: {r['ni_number']}. Email: {r['email']}. "
        f"Phone: {r['phone']}. Case type: {r['case_type']}. Reference: {r['canary']}."
    )
    return {
        "chunk_id": f"{r['doc_id']}#0",
        "doc_id": r["doc_id"],
        "source": f"internal://{r['doc_id']}",
        "title": f"Case note {r['doc_id']}",
        "text": text,
        "trust": "restricted",
        "role": "staff",
    }
