# INTILY Project Status — 2026-09-05

## Current architecture

Production publication is still running on the proven pre-limit baseline while the repository boundary is being migrated. The canonical source for the news subsystem is now `knyavik-stack/intily-news`.

The production scheduler/runtime has not yet been switched to this repository in this split step because the existing GitHub Actions workflow depends on four repository secrets that are present in `synapsemax` but not transferable as plaintext through the GitHub API. This is an intentional safety hold: publications must not be interrupted merely to make the repository boundary change.

## Repository split

- New repository: `knyavik-stack/intily-news` (private).
- Migration commit: `ea85fa33e2ecd2af34a73fc9fefdaf288e054d8f`.
- Migrated: publisher code, workflow, state, Intily documentation and historical backups.
- SynapseMax cleanup is prepared in branch `chore/remove-intily-from-synapsemax`; production `main` is deliberately untouched until the runtime switch is verified.

## Production baseline

Rollback baseline used for the split: 2026-09-05 08:00 MSK / 05:00 UTC.

## GitHub Actions dependency

The current publisher workflow requires repository secrets:
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `OPENAI_API_KEY`

plus the built-in `GITHUB_TOKEN`. The source repository currently has four Actions secrets in total; the fourth is not consumed by the workflow environment above.

GitHub does not reveal secret values through its secrets API. Therefore secret values cannot be silently copied from one private repository to another. Before the new repository becomes the active GitHub-hosted publisher, the required provider secrets must exist in `intily-news`, or the runtime must be migrated away from GitHub-hosted Actions.

## Next architectural objective

Move the production execution path away from GitHub-hosted runner minutes while keeping `intily-news` as the canonical source repository. This is the next step and must be designed so that repository separation, secrets, state and publication cadence remain intact.

## Safety rule

Do not delete the Intily publisher from `synapsemax/main` until the new runtime has been smoke-tested end-to-end. The cleanup branch is intentionally ready for the final merge once the runtime cutover is proven.
