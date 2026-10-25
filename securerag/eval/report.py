"""Build the results table, charts and variance table from the run records.

Run: python -m securerag.eval.report      (works on partial results; says how many are finished)
Writes to results/: results_table.csv, results_table.md, variance_table.csv, and three charts.
"""

import csv
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from securerag.config import CONFIGS  # noqa: E402
from securerag.eval.metrics import summarize  # noqa: E402
from securerag.eval.run_eval import load_records  # noqa: E402

RUNS = Path("results/runs")
OUT = Path("results")
KINDS = ("poisoning", "indirect_injection", "direct_injection", "leakage")
BASELINE = "none"


def fmt(r: dict) -> str:
    if not r["n"]:
        return "n/a"
    return f"{r['rate']:.0%} [{r['lo']:.0%}-{r['hi']:.0%}] ({r['k']}/{r['n']})"


def table_rows(summary: dict[str, dict]) -> list[dict]:
    rows = []
    for config in (c for c in CONFIGS if c in summary):
        s = summary[config]
        row = {"config": config}
        row.update({k: fmt(s["asr"][k]) if k in s["asr"] else "n/a" for k in KINDS})
        row.update(
            {
                "all attacks": fmt(s["asr_all"]),
                "clean accuracy": fmt(s["accuracy"]),
                "false blocks": fmt(s["false_block"]),
                "false flags": fmt(s["false_flag"]),
                "LLM calls/query": f"{s['calls_per_query']:.2f}",
                "Prompt Guard calls/query": f"{s['guard_calls_per_query']:.2f}",
            }
        )
        rows.append(row)
    # A system that refuses everything is the other simple baseline: perfectly safe, useless.
    rows.append({"config": "refuse-everything (analytic)", **dict.fromkeys(KINDS, "0%"),
                 "all attacks": "0%", "clean accuracy": "0%", "false blocks": "100%",
                 "false flags": "100%", "LLM calls/query": "0.00",
                 "Prompt Guard calls/query": "0.00"})  # fmt: skip
    return rows


def write_table(rows: list[dict], out: Path) -> None:
    cols = list(rows[0])
    with (out / "results_table.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
    (out / "results_table.md").write_text(
        "Rates are shown as rate [95% Wilson interval] (k/n). Baseline: `none`.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )


def variance_rows(repeat_runs: list[list[dict]]) -> list[dict]:
    """Mean and standard deviation of attack success and accuracy across repeat runs."""
    per_run = [summarize(r) for r in repeat_runs if r]
    rows = []
    for config in (c for c in CONFIGS if any(c in s for s in per_run)):
        asr = [s[config]["asr_all"]["rate"] for s in per_run if config in s]
        acc = [s[config]["accuracy"]["rate"] for s in per_run if config in s]

        def ms(xs):
            return (
                statistics.mean(xs),
                statistics.stdev(xs) if len(xs) > 1 else float("nan"),
            )

        (am, asd), (cm, csd) = ms(asr), ms(acc)
        rows.append({"config": config, "runs": len(asr), "asr_mean": round(am, 3),
                     "asr_sd": round(asd, 3), "accuracy_mean": round(cm, 3),
                     "accuracy_sd": round(csd, 3)})  # fmt: skip
    return rows


def _bars(ax, labels, series, title):
    width = 0.8 / max(1, len(series))
    for i, (name, vals) in enumerate(series.items()):
        xs = [j + i * width for j in range(len(labels))]
        err = [[v[0] - v[1] for v in vals], [v[2] - v[0] for v in vals]]
        ax.bar(xs, [v[0] for v in vals], width, label=name, yerr=err, capsize=2)
    ax.set_xticks([j + 0.4 - width / 2 for j in range(len(labels))], labels)
    ax.set_ylim(0, 1.05)
    ax.set_title(title)


def charts(summary: dict[str, dict], out: Path) -> None:
    configs = [c for c in CONFIGS if c in summary]
    # 1. Attack success per attack kind and configuration, with 95% intervals.
    fig, ax = plt.subplots(figsize=(10, 4.5))
    series = {
        k: [
            (
                summary[c]["asr"].get(k, {"rate": 0, "lo": 0, "hi": 0})["rate"],
                summary[c]["asr"].get(k, {"rate": 0, "lo": 0, "hi": 0})["lo"],
                summary[c]["asr"].get(k, {"rate": 0, "lo": 0, "hi": 0})["hi"],
            )
            for c in configs
        ]
        for k in KINDS
    }
    _bars(ax, configs, series, "Attack success rate by configuration (lower is better)")
    ax.set_ylabel("attack success rate")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "chart_attack_success.png", dpi=130)
    plt.close(fig)
    # 2. Security versus usefulness.
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    for c in configs:
        x, y = summary[c]["asr_all"]["rate"], summary[c]["accuracy"]["rate"]
        ax.scatter(x, y)
        ax.annotate(c, (x, y), textcoords="offset points", xytext=(4, 4), fontsize=8)
    ax.set_xlabel("attack success rate (all attacks)")
    ax.set_ylabel("clean accuracy")
    ax.set_title("Security versus usefulness (top left is best)")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    fig.tight_layout()
    fig.savefig(out / "chart_tradeoff.png", dpi=130)
    plt.close(fig)
    # 3. Cost: false blocks and extra calls.
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4))
    a1.bar(configs, [summary[c]["false_block"]["rate"] for c in configs])
    a1.set_title("False-block rate on clean questions")
    a1.set_ylim(0, 1)
    a2.bar(configs, [summary[c]["calls_per_query"] for c in configs])
    a2.set_title("Answer-model calls per query")
    for a in (a1, a2):
        a.tick_params(axis="x", labelrotation=45)
    fig.tight_layout()
    fig.savefig(out / "chart_cost.png", dpi=130)
    plt.close(fig)


def main(runs: Path = RUNS, out: Path = OUT) -> None:
    full = load_records(runs / "full.jsonl")
    if not full:
        print("No finished records yet.")
        return
    summary = summarize(full)
    rows = table_rows(summary)
    write_table(rows, out)
    charts(summary, out)
    repeats = [load_records(p) for p in sorted(runs.glob("repeat_r*.jsonl"))]
    var = variance_rows(repeats)
    if var:
        with (out / "variance_table.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(var[0]))
            w.writeheader()
            w.writerows(var)
    done = {c: s["n_queries"] for c, s in summary.items()}
    print(f"{len(full)} records; queries per configuration so far: {done}")


if __name__ == "__main__":
    main()
