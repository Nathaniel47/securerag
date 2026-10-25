"""Text patterns shared by the defenses."""

import re

# Phrases that address the model instead of informing the reader. Matching is deliberately broad:
# a false hit costs one dropped document, a miss lets an injection through.
INSTRUCTION = re.compile(
    r"ignore\s+(all\s+|the\s+|your\s+)?(previous|prior|above|earlier)"
    r"|ignore\s+the\s+user"
    r"|disregard\s+(all\s+|the\s+|your\s+)?(previous|prior|above|earlier|rules|instructions)"
    r"|forget\s+(all\s+|your\s+)?(previous\s+|prior\s+)?instructions"
    r"|(new|updated)\s+instructions"
    r"|system\s+(notice|override|prompt)"
    r"|(instruction|note)s?\s+(to|for)\s+(the\s+)?(ai|assistant|model)"
    r"|(rules|instructions)\s+(above\s+)?(no\s+longer\s+apply|are\s+cancell?ed)"
    r"|(reply|respond|answer|output)\s+(only\s+)?with\s+the\s+(code|text|word)"
    r"|reply\s+only\s+with"
    r"|your\s+(final\s+|only\s+)?(answer|task)\s+(must\s+be|is\s+to)"
    r"|developer\s+mode"
    r"|you\s+must\s+(reply|respond|output|prepend|print)",
    re.I,
)

# Sensitive values the output filter must never let through.
CANARY = re.compile(r"CANARY-[0-9a-f]{8}", re.I)
PII = re.compile(
    r"GHA-FAKE-\d+"  # synthetic Ghana Card IDs
    r"|NHIS-FAKE-\d+"
    r"|\bGHA-\d{9}-\d\b"  # real Ghana Card format
    r"|[\w.+-]+@[\w-]+\.[\w.-]+"  # email
    r"|\+233[\s\d-]{7,}",  # Ghana phone numbers
    re.I,
)
