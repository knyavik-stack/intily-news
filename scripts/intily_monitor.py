#!/usr/bin/env python3
"""Intily production KPI dashboard and monitoring CLI.

Reads only the durable publisher state; it never contacts Telegram or providers.
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone

# OPERATOR CONTROL:
# ALERT_NO_PUBLISH_RUNS controls the RED threshold for consecutive successful
# cycles with no publication. Set to 0 to disable this alert only.
ALERT_NO_PUBLISH_RUNS = 10
# ALERT_ITEM_FAILURES_24H controls the RED threshold for item publication
# failures in the last 24h. Set to 0 to disable this alert only.
ALERT_ITEM_FAILURES_24H = 3
STATE_FILE = os.environ.get("STATE_FILE", "data/intily-ai-news-state.json")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dt(ts):
    if not ts:
        return "—"
    return datetime.fromtimestamp(float(ts), timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def summarize(items):
    n = len(items)
    published = sum(int(x.get("published", 0) or 0) for x in items)
    failures = sum(int(x.get("item_failures", 0) or 0) for x in items)
    candidates = sum(int(x.get("candidates", 0) or 0) for x in items)
    queue = sum(int(x.get("queue_after", 0) or 0) for x in items)
    no_publish = sum(1 for x in items if x.get("business_result") != "PUBLISHED")
    return {
        "runs": n,
        "published": published,
        "no_publish": no_publish,
        "publish_rate": round(published * 100 / n, 1) if n else 0.0,
        "avg_candidates": round(candidates / n, 1) if n else 0.0,
        "avg_queue_after": round(queue / n, 1) if n else 0.0,
        "item_failures": failures,
    }


def dashboard(state, now=None):
    now = now or time.time()
    history = state.get("run_history", [])
    last = history[-1] if history else None
    last_24h = [x for x in history if now - float(x.get("ts", 0) or 0) <= 86400]
    last_7d = [x for x in history if now - float(x.get("ts", 0) or 0) <= 7 * 86400]
    consecutive = 0
    for x in reversed(history):
        if x.get("business_result") == "PUBLISHED":
            break
        consecutive += 1
    h = state.get("health", {})
    lines = [
        "# Intily Production KPI",
        "",
        f"**Generated:** {dt(now)}",
        f"**Monitoring:** {'ON' if state.get('kpi_monitoring_enabled', True) else 'OFF'}",
        "",
        "## Current",
        "",
        f"- Business result: **{(last or {}).get('business_result', 'NO_DATA')}**",
        f"- Reason: `{(last or {}).get('business_reason', '—')}`",
        f"- Last cycle: {dt((last or {}).get('ts'))}",
        f"- Candidates: {(last or {}).get('candidates', '—')}",
        f"- Queue: {(last or {}).get('queue_after', '—')}",
        f"- Published: {(last or {}).get('published', '—')}",
        f"- Publish attempts: {(last or {}).get('publish_attempts', '—')}",
        f"- Item failures: {(last or {}).get('item_failures', '—')}",
        f"- Consecutive no-publish cycles: **{consecutive}**",
        f"- Publisher health: **{h.get('last_status', '—')}**",
        "",
        "## Rolling KPI",
        "",
        "| Window | Runs | Published | No publish | Publish rate | Avg candidates | Avg queue | Item failures |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, items in (("24h", last_24h), ("7d", last_7d), ("Stored history", history)):
        s = summarize(items)
        lines.append(f"| {label} | {s['runs']} | {s['published']} | {s['no_publish']} | {s['publish_rate']}% | {s['avg_candidates']} | {s['avg_queue_after']} | {s['item_failures']} |")
    lines += ["", "## Recent cycles", "", "| Time | Business result | Reason | Candidates | Queue after | Published | Failures |", "|---|---|---|---:|---:|---:|---:|"]
    for x in reversed(history[-20:]):
        lines.append(f"| {dt(x.get('ts'))} | **{x.get('business_result','—')}** | `{x.get('business_reason','—')}` | {x.get('candidates',0)} | {x.get('queue_after',0)} | {x.get('published',0)} | {x.get('item_failures',0)} |")
    return "\n".join(lines), consecutive, sum(int(x.get("item_failures", 0) or 0) for x in last_24h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=STATE_FILE)
    ap.add_argument("--check", action="store_true", help="exit 1 on configured RED thresholds")
    args = ap.parse_args()
    state = load(args.state)
    text, consecutive, failures_24h = dashboard(state)
    print(text)
    if args.check:
        alerts = []
        if ALERT_NO_PUBLISH_RUNS and consecutive >= ALERT_NO_PUBLISH_RUNS:
            alerts.append(f"{consecutive} consecutive no-publish cycles")
        if ALERT_ITEM_FAILURES_24H and failures_24h >= ALERT_ITEM_FAILURES_24H:
            alerts.append(f"{failures_24h} item publication failures in 24h")
        if alerts:
            print("\n## ALERT — RED\n\n" + "\n".join(f"- {x}" for x in alerts))
            raise SystemExit(1)
        print("\n## Monitor status — GREEN\n")


if __name__ == "__main__":
    main()
