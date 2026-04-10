#!/usr/bin/env python3
"""
AI Dashboard Insights Generator
================================
Reads the last 14 days of test run data from metrics/runs.jsonl and produces
a plain-English summary saved to metrics/latest_insight.txt.

Called by the metrics-collector workflow after publishing the dashboard.

Usage:
    python dashboard/generate_insights.py
    python dashboard/generate_insights.py --days 7
    python dashboard/generate_insights.py --runs-file path/to/runs.jsonl

Output:
    metrics/latest_insight.txt   — rendered in the dashboard HTML
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("[generate_insights] openai not installed — skipping insight generation.")
    sys.exit(0)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    cfg = PROJECT_ROOT / "settings.cfg"
    if cfg.exists():
        for line in cfg.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY"):
                _, _, value = line.partition("=")
                value = value.strip()
                if value:
                    return value
    return ""


def _load_recent_runs(runs_file: Path, days: int) -> list[dict]:
    if not runs_file.exists():
        return []
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    runs = []
    for line in runs_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            ts = obj.get("timestamp_utc", "")
            if not ts:
                continue
            t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if t >= cutoff:
                runs.append(obj)
        except Exception:
            continue
    return runs


SYSTEM_PROMPT = """\
You are a QA engineering lead reviewing automated test run data for CommCare Connect.
The data covers web and mobile tests run against stage and prod environments.

Write a plain-English insight summary with exactly 4 short sentences:
1. Overall pass rate and whether it has been trending up, down, or stable.
2. The single worst day or environment and the most likely reason (e.g. deployment, flakiness).
3. Any environment (stage/prod) or scope (web/mobile) that is consistently underperforming.
4. One specific, actionable recommendation for the QA team.

Tone: professional, concise, factual. No bullet points. No markdown. Pure prose.
Maximum 120 words total.
"""


def generate_insight(runs: list[dict]) -> str:
    if not runs:
        return "No test run data available for the selected period."

    # Build a compact summary to stay within token limits
    summary_rows = []
    for r in runs:
        summary_rows.append({
            "date":    r.get("timestamp_utc", "")[:10],
            "env":     r.get("env", "?"),
            "scope":   r.get("scope", "?"),
            "passed":  r.get("passed", 0),
            "failed":  r.get("failed", 0),
            "skipped": r.get("skipped", 0),
            "status":  r.get("status", "?"),
        })

    data_json = json.dumps(summary_rows, indent=2)
    if len(data_json) > 6000:
        data_json = data_json[:6000] + "\n... [truncated]"

    api_key = _load_api_key()
    if not api_key:
        return "AI insight unavailable — OPENAI_API_KEY not configured."

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                f"Here are the test runs for the last {len(set(r['date'] for r in summary_rows))} days:\n\n{data_json}"
            },
        ],
    )
    return response.choices[0].message.content.strip()


def main():
    parser = argparse.ArgumentParser(description="Generate AI insights from test run metrics.")
    parser.add_argument("--days", type=int, default=14,
                        help="Number of days to analyse (default: 14)")
    parser.add_argument("--runs-file", default=None,
                        help="Path to runs.jsonl (default: metrics/runs.jsonl)")
    args = parser.parse_args()

    runs_file = Path(args.runs_file) if args.runs_file else PROJECT_ROOT / "metrics" / "runs.jsonl"
    output_file = PROJECT_ROOT / "metrics" / "latest_insight.txt"

    runs = _load_recent_runs(runs_file, args.days)
    print(f"[generate_insights] Loaded {len(runs)} runs from the last {args.days} days.")

    if not runs:
        insight = "No test run data found for the selected period."
    else:
        print("[generate_insights] Calling OpenAI for insight …")
        insight = generate_insight(runs)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(insight, encoding="utf-8")

    print(f"\n[generate_insights] Insight written → {output_file}")
    print(f"\n--- Insight ---\n{insight}\n")


if __name__ == "__main__":
    main()
