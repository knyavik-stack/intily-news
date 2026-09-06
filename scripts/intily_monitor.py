#!/usr/bin/env python3
"""Intily production KPI dashboard and read-only health check.

Reads only data/intily-ai-news-state.json. It never contacts Telegram, RSS, or AI providers.
The dashboard is intentionally Markdown-first so GitHub Actions Summary is the operator UI.
"""
import argparse
import json
import sys
import time
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parents[1] / 'data' / 'intily-ai-news-state.json'

# Hard RED thresholds. These are incident thresholds, not editorial targets.
ALERT_NO_PUBLISH_RUNS = 10
ALERT_PUBLISH_FAILURES_24H = 5
ALERT_PUBLISH_FAILURE_RATE = 20.0
ALERT_RSS_ERROR_RATE = 25.0

# Diagnostic thresholds are shown as WARN and do not fail the workflow.
WARN_PUBLISH_FAILURES_24H = 3
WARN_PUBLISH_FAILURE_RATE = 10.0
WARN_ADMISSION_RATE = 10.0
MIN_RATE_SAMPLE_ATTEMPTS = 10
MIN_ADMISSION_SAMPLE = 50


def load(path=STATE_PATH):
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def rows(state):
    return state.get('run_history', []) if state.get('kpi_monitoring_enabled', True) else []


def window(data, seconds, now):
    return [r for r in data if now - float(r.get('ts', 0) or 0) <= seconds]


def sums(data):
    pubs = sum(int(r.get('published', 0) or 0) for r in data)
    attempts = sum(int(r.get('publish_attempts', 0) or 0) for r in data)
    failures = sum(int(r.get('item_failures', 0) or 0) for r in data)
    candidates = sum(int(r.get('candidates', 0) or 0) for r in data)
    admission_rows = [r for r in data if r.get('admission') and 'candidate_count' in r.get('admission', {})]
    observed_candidates = sum(int(r.get('admission', {}).get('candidate_count', 0) or 0) for r in admission_rows)
    added = sum(int(r.get('admission', {}).get('added', 0) or 0) for r in admission_rows)
    no_publish = sum(1 for r in data if r.get('business_result') == 'NO_PUBLISH')
    no_publish_reasons = {}
    admission_blocks = {}
    provider_used = {}
    failovers = 0
    rss_raw = rss_errors = rss_attempts = direct_raw = direct_errors = 0
    source_counts = {}
    q_values = [float(r.get('queue_after', 0) or 0) for r in data]
    q_deltas = [float(r.get('queue_after', 0) or 0) - float(r.get('queue_before', 0) or 0) for r in data]
    pub_ts = [float(r.get('ts', 0) or 0) for r in data if r.get('published')]
    for r in data:
        if r.get('business_result') == 'NO_PUBLISH':
            reason = r.get('business_reason', 'unknown')
            no_publish_reasons[reason] = no_publish_reasons.get(reason, 0) + 1
        a = r.get('admission', {})
        block = a.get('dominant_block')
        if block and block != 'none':
            admission_blocks[block] = admission_blocks.get(block, 0) + 1
        p = r.get('provider', {})
        used = p.get('used')
        if used:
            provider_used[used] = provider_used.get(used, 0) + 1
        failovers += int(p.get('failovers', 0) or 0)
        rss = r.get('rss', {})
        rss_raw += int(rss.get('raw_items', 0) or 0)
        rss_errors += int(rss.get('query_errors', 0) or 0)
        rss_attempts += int(rss.get('queries_attempted', 0) or 0)
        direct_raw += int(rss.get('direct_raw_items', 0) or 0)
        direct_errors += int(rss.get('direct_feed_errors', 0) or 0)
        for source, count in rss.get('source_counts', {}).items():
            # -1 means feed error; the error is counted separately, never as yield.
            source_counts[source] = source_counts.get(source, 0) + max(0, int(count or 0))
    intervals = [(b-a)/60 for a, b in zip(pub_ts, pub_ts[1:]) if b > a]
    span_hours = (data[-1]['ts'] - data[0]['ts']) / 3600 if len(data) > 1 else 0
    return {
        'cycles': len(data), 'searches': sum(1 for r in data if r.get('searched')),
        'candidates': candidates, 'avg_candidates': candidates / max(1, len(data)),
        'published': pubs, 'publication_rate': pubs / max(1, len(data)) * 100,
        'publish_frequency': pubs / max(1, span_hours) if span_hours else 0,
        'avg_publish_interval': sum(intervals) / len(intervals) if intervals else None,
        'attempts': attempts, 'failures': failures,
        'failure_rate': failures / max(1, attempts) * 100,
        'no_publish': no_publish, 'no_publish_rate': no_publish / max(1, len(data)) * 100,
        'no_publish_reasons': no_publish_reasons,
        'admission_candidates': observed_candidates, 'admission_added': added,
        'admission_rate': added / max(1, observed_candidates) * 100,
        'admission_blocks': admission_blocks,
        'rss_raw': rss_raw, 'rss_errors': rss_errors, 'rss_attempts': rss_attempts,
        'direct_raw': direct_raw, 'direct_errors': direct_errors, 'source_counts': source_counts,
        'rss_error_rate': rss_errors / max(1, rss_attempts) * 100,
        'provider_used': provider_used, 'failovers': failovers,
        'queue_avg': sum(q_values) / len(q_values) if q_values else 0,
        'queue_max': max(q_values) if q_values else 0,
        'queue_velocity': sum(q_deltas) / len(q_deltas) if q_deltas else 0,
    }


def pct(value):
    return f'{value:.1f}%'


def top_items(mapping, limit=6):
    return sorted(mapping.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]


def print_dashboard(state):
    data = rows(state)
    now = time.time()
    d24 = sums(window(data, 86400, now))
    d7 = sums(window(data, 7 * 86400, now))
    stored = sums(data)
    health = state.get('health', {})
    last = data[-1] if data else {}
    consecutive_no_publish = 0
    for r in reversed(data):
        if r.get('business_result') == 'NO_PUBLISH':
            consecutive_no_publish += 1
        else:
            break

    hard, warnings = evaluate(data, d24)
    status = '🔴 RED' if hard else ('🟡 WARN' if warnings else '🟢 GREEN')
    last_result = last.get('business_result', 'UNKNOWN')
    last_reason = last.get('business_reason', '')

    print(f'# Intily Production Monitor — {status}')
    print('')
    print(f'> **Last cycle:** `{last_result}` — `{last_reason}`  ')
    print(f'> **Technical health:** `{health.get("last_status", "UNKNOWN")}` · **Queue:** `{len(state.get("queue", []))}` · **Consecutive NO_PUBLISH:** `{consecutive_no_publish}`')
    print('')
    print('## Executive KPI')
    print('')
    print('| KPI | 24h | 7d | Stored |')
    print('|---|---:|---:|---:|')
    print(f"| Cycles | {d24['cycles']} | {d7['cycles']} | {stored['cycles']} |")
    print(f"| Publications | {d24['published']} | {d7['published']} | {stored['published']} |")
    print(f"| Publication rate | {pct(d24['publication_rate'])} | {pct(d7['publication_rate'])} | {pct(stored['publication_rate'])} |")
    print(f"| Frequency | {d24['publish_frequency']:.2f}/h | {d7['publish_frequency']:.2f}/h | — |")
    print(f"| Candidates | {d24['candidates']} | {d7['candidates']} | {stored['candidates']} |")
    print(f"| NO_PUBLISH | {d24['no_publish']} ({pct(d24['no_publish_rate'])}) | {d7['no_publish']} ({pct(d7['no_publish_rate'])}) | {stored['no_publish']} |")
    print(f"| PUBLISH_FAILED | {d24['failures']} ({pct(d24['failure_rate'])}) | {d7['failures']} ({pct(d7['failure_rate'])}) | {stored['failures']} |")
    print('')

    print('## Discovery → Admission → Publication')
    print('')
    print('| Stage | 24h | Rate / signal |')
    print('|---|---:|---:|')
    print(f"| RSS raw items | {d24['rss_raw']} | — |")
    print(f"| Candidates | {d24['candidates']} | {pct(d24['candidates'] / max(1, d24['rss_raw']) * 100)} of raw |")
    print(f"| Admitted to queue | {d24['admission_added']} | {pct(d24['admission_rate'])} of telemetry-covered candidates |")
    print(f"| Published | {d24['published']} | {pct(d24['published'] / max(1, d24['admission_added']) * 100)} of admitted |")
    print(f"| Queue velocity | {d24['queue_velocity']:+.2f}/cycle | avg delta |")
    print('')

    print('## Provider / RSS health')
    print('')
    print('| Signal | 24h |')
    print('|---|---:|')
    print(f"| Google News queries | {d24['rss_attempts']} attempted / {d24['rss_errors']} errors |")
    print(f"| Direct feeds | {d24['direct_raw']} items / {d24['direct_errors']} errors |")
    print(f"| RSS query error rate | {pct(d24['rss_error_rate'])} |")
    print(f"| AI providers used | {', '.join(f'{k}: {v}' for k, v in top_items(d24['provider_used'])) or 'none in window'} |")
    print(f"| Failovers | {d24['failovers']} |")
    print('')

    if d24['source_counts']:
        print('### Source yield')
        print('')
        print('| Source | Fresh items |')
        print('|---|---:|')
        for source, count in top_items(d24['source_counts'], 8):
            print(f'| {source} | {count} |')
        print('')

    print('## NO_PUBLISH classification')
    print('')
    print('| Reason | 24h cycles |')
    print('|---|---:|')
    for reason, count in top_items(d24['no_publish_reasons'], 10):
        print(f'| `{reason}` | {count} |')
    if not d24['no_publish_reasons']:
        print('| — | 0 |')
    print('')

    print('## Admission blocks')
    print('')
    print('| Block | 24h cycles |')
    print('|---|---:|')
    for reason, count in top_items(d24['admission_blocks'], 10):
        print(f'| `{reason}` | {count} |')
    if not d24['admission_blocks']:
        print('| — | 0 |')
    print('')

    print('## Alerts & diagnostics')
    print('')
    if hard:
        for item in hard:
            print(f'- 🔴 **RED:** {item}')
    if warnings:
        for item in warnings:
            print(f'- 🟡 **WARN:** {item}')
    if not hard and not warnings:
        print('- 🟢 No active alerts.')
    print('')
    print('> Alert thresholds are incident guards. Editorial targets such as admission rate are diagnostic signals until a statistically meaningful sample establishes an SLO.')
    print('')

    print('<details>')
    print('<summary>Recent 12 production cycles</summary>')
    print('')
    print('| UTC | Result | Reason | Cand. | Add | Pub. | Fail | Provider |')
    print('|---|---|---|---:|---:|---:|---:|---|')
    for r in data[-12:]:
        a = r.get('admission', {})
        p = r.get('provider', {})
        print(f"| {time.strftime('%m-%d %H:%M', time.gmtime(r.get('ts', 0)))} | {r.get('business_result','-')} | `{r.get('business_reason','')}` | {r.get('candidates',0)} | {a.get('added',0)} | {r.get('published',0)} | {r.get('item_failures',0)} | {p.get('used') or '-'} |")
    print('')
    print('</details>')


def evaluate(data, d24):
    hard = []
    warnings = []
    consecutive = 0
    for r in reversed(data):
        if r.get('business_result') == 'NO_PUBLISH':
            consecutive += 1
        else:
            break

    if ALERT_NO_PUBLISH_RUNS and consecutive >= ALERT_NO_PUBLISH_RUNS:
        hard.append(f'NO_PUBLISH streak {consecutive} >= {ALERT_NO_PUBLISH_RUNS}')

    if ALERT_PUBLISH_FAILURES_24H and d24['attempts'] >= MIN_RATE_SAMPLE_ATTEMPTS:
        if d24['failures'] >= ALERT_PUBLISH_FAILURES_24H and d24['failure_rate'] >= ALERT_PUBLISH_FAILURE_RATE:
            hard.append(f'PUBLISH_FAILED 24h {d24["failures"]}/{d24["attempts"]} ({d24["failure_rate"]:.1f}%) >= incident threshold {ALERT_PUBLISH_FAILURE_RATE:.0f}%')
        elif d24['failures'] >= WARN_PUBLISH_FAILURES_24H and d24['failure_rate'] >= WARN_PUBLISH_FAILURE_RATE:
            warnings.append(f'PUBLISH_FAILED 24h {d24["failures"]}/{d24["attempts"]} ({d24["failure_rate"]:.1f}%) — elevated, below hard incident threshold')

    if ALERT_RSS_ERROR_RATE and d24['rss_attempts'] >= MIN_RATE_SAMPLE_ATTEMPTS and d24['rss_error_rate'] >= ALERT_RSS_ERROR_RATE:
        hard.append(f'RSS query error rate {d24["rss_error_rate"]:.1f}% >= {ALERT_RSS_ERROR_RATE:.1f}%')

    latest = sums(data[-1:]) if data else sums([])
    if latest['candidates'] and latest['admission_added'] == 0:
        warnings.append('latest cycle has candidates but zero queue admissions')

    if d24['admission_candidates'] >= MIN_ADMISSION_SAMPLE and d24['admission_rate'] < WARN_ADMISSION_RATE:
        warnings.append(f'24h admission rate {d24["admission_rate"]:.1f}% < diagnostic target {WARN_ADMISSION_RATE:.1f}%')

    if d24['direct_errors']:
        warnings.append(f'{d24["direct_errors"]} direct RSS feed errors in 24h; inspect source-level health')
    return hard, warnings


def check(state):
    data = rows(state)
    now = time.time()
    d24 = sums(window(data, 86400, now))
    hard, _warnings = evaluate(data, d24)
    if hard:
        print('MONITOR RED')
        for item in hard:
            print(' -', item)
        return 1
    print('MONITOR GREEN')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--state', default=str(STATE_PATH))
    args = parser.parse_args()
    state = load(Path(args.state))
    if args.check:
        sys.exit(check(state))
    print_dashboard(state)
