#!/usr/bin/env python3
"""Intily production KPI dashboard and read-only health check.

Reads only data/intily-ai-news-state.json. It never contacts Telegram, RSS, or AI providers.

CONFIGURATION: alert thresholds are at the top of this file. Set a threshold to 0 to disable
that alert. KPI collection itself is controlled in scripts/intily_ai_news.py.
"""
import argparse, json, sys, time
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parents[1] / 'data' / 'intily-ai-news-state.json'
ALERT_NO_PUBLISH_RUNS = 10
ALERT_ITEM_FAILURES_24H = 3
ALERT_RSS_ERROR_RATE = 25.0
ALERT_ADMISSION_RATE = 10.0


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
    added = sum(int(r.get('admission', {}).get('added', 0) or 0) for r in data)
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
            source_counts[source] = source_counts.get(source, 0) + max(0, int(count or 0))
    intervals = [(b-a)/60 for a,b in zip(pub_ts, pub_ts[1:]) if b>a]
    return {
        'cycles': len(data), 'searches': sum(1 for r in data if r.get('searched')),
        'candidates': candidates, 'avg_candidates': candidates/max(1,len(data)),
        'published': pubs, 'publication_rate': pubs/max(1,len(data))*100,
        'publish_frequency': pubs/(max(1,(data[-1]['ts']-data[0]['ts'])/3600)) if len(data)>1 else 0,
        'avg_publish_interval': sum(intervals)/len(intervals) if intervals else None,
        'attempts': attempts, 'failures': failures,
        'failure_rate': failures/max(1,attempts)*100,
        'no_publish': no_publish, 'no_publish_rate': no_publish/max(1,len(data))*100,
        'no_publish_reasons': no_publish_reasons,
        'admission_candidates': candidates, 'admission_added': added,
        'admission_rate': added/max(1,candidates)*100,
        'admission_blocks': admission_blocks,
        'rss_raw': rss_raw, 'rss_errors': rss_errors, 'direct_raw': direct_raw, 'direct_errors': direct_errors, 'source_counts': source_counts,
        'rss_error_rate': rss_errors/max(1,rss_attempts)*100,
        'provider_used': provider_used, 'failovers': failovers,
        'queue_avg': sum(q_values)/len(q_values) if q_values else 0,
        'queue_max': max(q_values) if q_values else 0,
        'queue_velocity': sum(q_deltas)/len(q_deltas) if q_deltas else 0,
    }


def print_dashboard(state):
    data = rows(state)
    now = time.time()
    d24 = sums(window(data, 86400, now))
    d7 = sums(window(data, 7*86400, now))
    stored = sums(data)
    health = state.get('health', {})
    last = data[-1] if data else {}
    consecutive_no_publish = 0
    for r in reversed(data):
        if r.get('business_result') == 'NO_PUBLISH': consecutive_no_publish += 1
        else: break
    print('INTILY PRODUCTION DASHBOARD')
    print('=' * 72)
    print(f"KPI monitoring: {'ENABLED' if state.get('kpi_monitoring_enabled', True) else 'DISABLED'}")
    print(f"Technical health: {health.get('last_status','UNKNOWN')} | last run: {last.get('business_result','UNKNOWN')} / {last.get('business_reason','')}")
    print(f"Queue: {len(state.get('queue', []))} | known: {len(state.get('known', {}))} | published memory: {len(state.get('published', {}))} | stories: {len(state.get('stories', {}))}")
    print(f"Consecutive NO_PUBLISH: {consecutive_no_publish}")
    print('24H')
    print(f"  cycles={d24['cycles']} searches={d24['searches']} candidates={d24['candidates']} avg_candidates={d24['avg_candidates']:.2f}")
    print(f"  published={d24['published']} publication_rate={d24['publication_rate']:.2f}% frequency={d24['publish_frequency']:.2f}/h")
    print(f"  attempts={d24['attempts']} PUBLISH_FAILED={d24['failures']} failure_rate={d24['failure_rate']:.2f}%")
    print(f"  NO_PUBLISH={d24['no_publish']} ({d24['no_publish_rate']:.2f}%)")
    print(f"  admission={d24['admission_added']}/{d24['admission_candidates']} ({d24['admission_rate']:.2f}%) blocks={d24['admission_blocks']}")
    print(f"  RSS google_raw={d24['rss_raw']} direct_raw={d24['direct_raw']} query_errors={d24['rss_errors']} direct_errors={d24['direct_errors']} error_rate={d24['rss_error_rate']:.2f}%")
    if d24['source_counts']: print(f"  source_yield={d24['source_counts']}")
    print(f"  providers_used={d24['provider_used']} failovers={d24['failovers']}")
    print(f"  queue_avg={d24['queue_avg']:.2f} queue_max={d24['queue_max']:.0f} velocity={d24['queue_velocity']:.2f}/cycle")
    if d24['no_publish_reasons']: print(f"  NO_PUBLISH reasons={d24['no_publish_reasons']}")
    print('7D')
    print(f"  cycles={d7['cycles']} published={d7['published']} frequency={d7['publish_frequency']:.2f}/h admission_rate={d7['admission_rate']:.2f}% failure_rate={d7['failure_rate']:.2f}%")
    print('STORED SAMPLE')
    print(f"  cycles={stored['cycles']} published={stored['published']} avg_candidates={stored['avg_candidates']:.2f} avg_publish_interval={stored['avg_publish_interval']}")
    print('RECENT 20')
    for r in data[-20:]:
        a=r.get('admission',{}); p=r.get('provider',{}); rss=r.get('rss',{})
        print(f"  {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(r.get('ts',0)))} | {r.get('business_result')} | {r.get('business_reason')} | cand={r.get('candidates',0)} add={a.get('added',0)} pub={r.get('published',0)} fail={r.get('item_failures',0)} provider={p.get('used') or '-'} rss_err={rss.get('query_errors',0)}")


def check(state):
    data=rows(state); now=time.time(); d24=sums(window(data,86400,now)); d1=sums(data[-1:]) if data else sums([])
    consecutive=0
    for r in reversed(data):
        if r.get('business_result')=='NO_PUBLISH': consecutive+=1
        else: break
    alerts=[]
    if ALERT_NO_PUBLISH_RUNS and consecutive>=ALERT_NO_PUBLISH_RUNS: alerts.append(f'NO_PUBLISH streak {consecutive} >= {ALERT_NO_PUBLISH_RUNS}')
    if ALERT_ITEM_FAILURES_24H and d24['failures']>=ALERT_ITEM_FAILURES_24H: alerts.append(f'PUBLISH_FAILED 24h {d24["failures"]} >= {ALERT_ITEM_FAILURES_24H}')
    if ALERT_RSS_ERROR_RATE and d24['rss_error_rate']>=ALERT_RSS_ERROR_RATE: alerts.append(f'RSS query error rate {d24["rss_error_rate"]:.1f}% >= {ALERT_RSS_ERROR_RATE}%')
    if d1['candidates'] and d1['admission_added']==0: alerts.append('candidate starvation: candidates present but zero admitted in latest cycle')
    if d24['candidates'] and d24['admission_rate']<ALERT_ADMISSION_RATE: alerts.append(f'24h admission rate {d24["admission_rate"]:.1f}% < {ALERT_ADMISSION_RATE}%')
    if alerts:
        print('MONITOR RED')
        for x in alerts: print(' -',x)
        return 1
    print('MONITOR GREEN')
    return 0


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--state', default=str(STATE_PATH))
    args=parser.parse_args()
    state=load(Path(args.state))
    if args.check: sys.exit(check(state))
    print_dashboard(state)
