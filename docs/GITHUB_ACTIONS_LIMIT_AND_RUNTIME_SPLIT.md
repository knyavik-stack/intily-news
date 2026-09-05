# GitHub Actions limit — runtime split

GitHub Free includes 2,000 GitHub-hosted Actions minutes/month for private repositories; once the included quota is exhausted and no valid payment method is configured, usage is blocked. A one-minute scheduler with a publisher run every few minutes is therefore not an appropriate production runtime.

The repository split is designed to make the next runtime migration safe:

1. `intily-news` becomes the canonical source.
2. The existing publication behavior remains preserved as the rollback reference.
3. The production scheduler/runtime is moved away from GitHub-hosted minutes.
4. Only after end-to-end publication is proven is `synapsemax` cleaned permanently.

Do not place provider tokens or Telegram credentials into source files. GitHub Actions secrets are intentionally not committed to the repository.
