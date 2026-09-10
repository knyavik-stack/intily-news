# Intily — GitHub Actions incident 2026-09-10

## Symptom

Production workflow runs #911 and #912 failed in the `Проверка аналитики и политики` step. The news engine itself was skipped, so these runs could not provide a production publication result.

## Root cause

The production hardening adapter `scripts/intily_production_entrypoint.py` was changed during the Groq Cloudflare 1010 mitigation, but the existing regression suite still imported `_one_shot_gemini_chat`.

The adapter retained `_gemini_chat` but the compatibility wrapper `_one_shot_gemini_chat` had been removed. Python therefore failed during test-module import:

`ImportError: cannot import name '_one_shot_gemini_chat' from 'intily_production_entrypoint'`

This was a test/implementation contract regression, not an API-key or provider outage.

## Correction

Commit `3bff691abb8d1873968a1315f15975774145a7e9` restored `_one_shot_gemini_chat(prompt, token)` as a compatibility wrapper over `_gemini_chat`.

No provider behavior was reverted. The Groq User-Agent mitigation and provider credential-rotation logic remain intact.

## Verification

A fresh `Intily AI News Publisher` workflow dispatch was started from commit `3bff691abb8d1873968a1315f15975774145a7e9` as run #913.

The policy/test step passed in the live run, unlike runs #911/#912. The production engine then proceeded to execution; final publication outcome must be judged from the completed run, not from the successful test step alone.

## Preventive rule

When changing a production adapter, preserve or update all public/internal test contracts in the same change. Required sequence remains:

**inspect → root cause → fix → verify → document**.

A green commit is not production proof; a fresh workflow run on the corrected commit is required.
