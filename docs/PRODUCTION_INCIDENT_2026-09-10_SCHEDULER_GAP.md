# INTILY Production Observation — 2026-09-10 Scheduler Gap

## Observation

After GitHub Actions run #896 (`34443787796`) completed at approximately **06:06 UTC on 2026-09-10**, no newer `Intily AI News Publisher` workflow run was visible in the repository's workflow-run collection during the subsequent verification.

The latest observed run remains #896; the previous fresh-discovery run was #895 at approximately 06:01 UTC.

This is materially different from the previously observed normal Cloudflare → GitHub dispatch cadence.

## Repository evidence

The production workflow intentionally has only:

```yaml
on:
  workflow_dispatch:
```

and no GitHub-native cron. Its concurrency group is `intily-ai-news-production` with `cancel-in-progress: false`.

The versioned Cloudflare Worker source declares:

- Cron: `* * * * *` UTC;
- randomized 1-in-3 dispatch gate;
- GitHub Actions `workflow_dispatch` as the dispatch target.

The random gate can introduce individual gaps, but a multi-hour absence of workflow runs is not consistent with the previously observed operating cadence and should be treated as a scheduler health signal, not silently accepted as normal publication behavior.

## What can be concluded

- The GitHub workflow itself is valid and was executing successfully immediately before the gap.
- The Python production engine was healthy enough to complete fresh discovery in run #895.
- The current provider outage is a separate blocking condition for publication quality.
- There is no evidence from the GitHub side alone that proves whether the Cloudflare Worker stopped running, stopped dispatching, lost its dispatch token, or encountered a Worker-side error.
- No current Cloudflare connector is available in this execution environment, so direct Worker deployment/log inspection cannot be truthfully claimed.

## No unauthorized scheduler change

The repository must **not** add a second publisher cron merely to mask this observation. The canonical architecture remains Cloudflare scheduler → GitHub `workflow_dispatch` → publisher.

A future watchdog may monitor scheduler freshness, but it must not become a second publisher scheduler unless the architecture is explicitly re-approved.

## Required external verification

When Cloudflare access is available, inspect the `intily-ai-news` Worker for:

1. Cron trigger still present as `* * * * *` UTC.
2. Worker execution events after 06:06 UTC.
3. `GITHUB_DISPATCH` log entries.
4. Any `GITHUB_DISPATCH_FAILED` response, especially 401/403/404/429.
5. `GITHUB_DISPATCH_TOKEN` still valid and authorized to dispatch `knyavik-stack/intily-news` workflow `intily-ai-news.yml`.

Do not rotate or replace the token without evidence that authorization is actually the failure mode.

## Next action

The next available production run must execute the new provider fast-stop regression. If Cloudflare resumes dispatching, continue with live verification automatically. If the scheduler remains silent, the project remains YELLOW and the Cloudflare scheduler is the active blocker.
