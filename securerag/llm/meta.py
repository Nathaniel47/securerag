"""Read and update results/run_meta.json (model IDs, limits, settings, git commit)."""

import json
import subprocess
from pathlib import Path

META_PATH = Path("results/run_meta.json")


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def update_run_meta(path: Path = META_PATH, **fields) -> dict:
    meta = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    meta.update(fields)
    meta["git_commit"] = git_commit()
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return meta
