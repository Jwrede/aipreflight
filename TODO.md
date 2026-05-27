# aipreflight TODO

## Target

Rename and evolve this project into `aipreflight`.

Positioning:

> aipreflight checks whether an AI application is ready to ship by running quality, cost, latency, observability, and deployment readiness checks before traffic is routed.

The project should become the flagship proof for this positioning:

> I help teams turn AI prototypes into production-ready systems with evals, observability, CI/CD, cost controls, and deployment gates.

## Positioning and wedge

`aipreflight` should be positioned as:

> SRE-style preflight checks for modern AI applications.

More specifically:

> aipreflight brings the deployment discipline of CI gates, smoke tests, canaries, SLOs, and model validation to LLM apps, RAG systems, prompt changes, and AI features.

The important point: deployment readiness is not new. Classical software already has CI/CD gates, smoke tests, health checks, readiness probes, canary analysis, policy checks, and SLO-based rollouts. Classical ML already has model registries, model validation, data validation, drift monitoring, model quality monitoring, and model blessing workflows.

That means `aipreflight` should not claim:

- "We invented deployment readiness."
- "We invented MLOps."
- "We are a complete model deployment platform."
- "We replace MLflow, TFX, SageMaker, Vertex AI, Evidently, Seldon, BentoML, Prometheus, Grafana, or Kubernetes."

The credible claim is narrower and stronger:

> Normal software has mature deployment gates. Classical ML has mature model validation workflows. Modern AI applications often still ship prompt changes, RAG changes, model/provider changes, and AI features without equivalent preflight checks for quality, cost, latency, observability, and rollback readiness. `aipreflight` fills that gap.

## Market reality

This project sits between three mature categories:

1. Software delivery/SRE
   - CI/CD gates
   - smoke tests
   - health checks
   - canaries
   - SLOs
   - rollback workflows

2. Classical MLOps
   - model registry
   - model validation
   - data validation
   - drift monitoring
   - model quality monitoring
   - model approval/blessing

3. AI application engineering
   - LLM API calls
   - RAG pipelines
   - prompt versions
   - model/provider routing
   - token/cost budgets
   - eval datasets
   - AI-specific observability

`aipreflight` should live in category 3 while borrowing proven ideas from categories 1 and 2.

## Target user

Primary users:

- platform engineers asked to make AI features production-safe
- ML engineers moving prototypes into services
- backend engineers owning LLM/RAG features
- DevOps/SRE teams asked to support AI workloads
- startup teams shipping AI features without a full MLOps platform

Secondary users:

- engineering managers who need a release checklist for AI features
- consultants doing AI production readiness audits
- teams evaluating whether an AI prototype is ready for a customer pilot

Not the primary user:

- research teams only training models
- teams already fully standardized on a large managed MLOps platform
- teams only looking for a hosted LLM gateway
- teams only looking for dashboards

## Differentiation

The differentiator is not one individual check. Many tools already do individual pieces better than this project should.

`aipreflight` is valuable because it combines the checks into one release decision:

```text
Can we ship this AI change?

quality/evals        pass/fail
latency/TTFT         pass/fail
error rate           pass/fail
cost budget          pass/fail
observability        pass/fail/warn
deployment/runbook   pass/fail/warn
overall verdict      PASS or FAIL
```

That is the product promise:

> one preflight command, one readiness report, one deployment verdict.

## What makes AI preflight different from normal deployment checks

Normal deployment checks ask:

- Does the service start?
- Are tests passing?
- Are error rates and latency acceptable?
- Is the deployment config valid?
- Can we roll back?

AI preflight checks must also ask:

- Did answer quality regress?
- Did retrieval quality regress?
- Did a prompt change break important cases?
- Did the model/provider change behavior?
- Is token usage inside budget?
- Is cost per request inside budget?
- Are model, prompt version, token count, latency, cost, request ID, and error type observable?
- Is the system debuggable when users report a bad answer?
- Is there a rollback path for prompt, model, retrieval config, or provider routing?

This is the gap `aipreflight` should make visible.

## Messaging

Use these phrases:

- "SRE-style preflight checks for AI applications."
- "A deployment gate for LLM and RAG systems."
- "One readiness report for quality, cost, latency, observability, and rollout risk."
- "Bring CI/CD discipline to AI features."
- "Know whether an AI prototype is ready for production traffic."

Avoid these phrases:

- "Complete MLOps platform."
- "AI deployment platform."
- "Model monitoring replacement."
- "LLM gateway."
- "AI-first company transformation platform."
- "Works for every ML system."

The strongest short description:

> `aipreflight` is a CI/CD readiness gate for AI applications. It checks eval quality, LLM/RAG behavior, latency, errors, cost budgets, observability, and rollout readiness before traffic is routed.

## Portfolio story

For the career positioning, `aipreflight` should prove this:

> I can take an AI prototype and add the production layer around it.

The proof should be visible in the repo:

- eval gates show product quality discipline
- `llmprobe` integration shows user-path reliability measurement
- `tokentoll` integration shows cost awareness
- Prometheus/OpenTelemetry checks show observability discipline
- CI/CD exit codes show deployment integration
- reports show communication and operational clarity
- examples show the pattern works for hosted API apps, RAG apps, and self-hosted inference

This is why `aipreflight` should be the flagship project, while `llmprobe` and `tokentoll` remain supporting tools.

## Why this rename makes sense

`inference-readiness-kit` is accurate, but too narrow. It sounds like a toolkit only for teams hosting their own inference endpoints. That is useful, but many companies will call hosted APIs and still have the same production problems: broken prompts, rising cost, missing evals, weak observability, no rollout gate, no runbook, and no clear owner.

`aipreflight` is broader and easier to explain:

- "AI" says this applies to AI applications, not only vLLM or self-hosted inference.
- "Preflight" says it runs before shipping or routing traffic.
- The name naturally supports CI/CD gates, readiness reports, and operational checks.
- It keeps the strong current inference work instead of throwing it away.

The goal is not to build a giant platform. The goal is to build a small, credible readiness layer that orchestrates existing tools and produces a clear ship/block verdict.

## Product boundary

`aipreflight` should answer one question:

> Is this AI system ready for production traffic?

It should not become:

- an LLM gateway
- a vector database
- a tracing backend
- a dashboard replacement
- a complete MLOps platform
- a cloud deployment framework

It should integrate with those systems and turn their signals into one readiness decision.

## Final architecture

```text
AI app, RAG system, or inference endpoint
        |
        v
aipreflight
        |
        +-- llmprobe: external user-path latency, TTFT, throughput, errors
        +-- tokentoll: token usage, cost estimate, budget gate
        +-- evals: quality and regression checks
        +-- Prometheus/OpenTelemetry: service health and telemetry checks
        +-- CI/CD: machine-readable pass/fail for deployment gates
        +-- Markdown/HTML report: human-readable production readiness report
```

`llmprobe` and `tokentoll` stay as independent tools. `aipreflight` becomes the orchestration and decision layer that uses them.

## Repository rename checklist

- [x] Rename GitHub repository from `inference-readiness-kit` to `aipreflight`.
  - Why: the public project name should match the portfolio story and be easy to remember.
  - Done when: the GitHub URL is `https://github.com/Jwrede/aipreflight` and old links redirect.

- [x] Update local git remote.
  - What: change `origin` from the old repo URL to the new repo URL after the GitHub rename.
  - Why: pushes should go to the renamed public project.
  - Done when: `git remote -v` shows `aipreflight`.

- [x] Update `pyproject.toml`.
  - What: change package metadata from `inference-readiness-kit` to `aipreflight`.
  - Why: the installable package name should match the repo and CLI.
  - Done when: package metadata, description, and project URLs use `aipreflight`.

- [x] Update README title, intro, clone command, and repo links.
  - What: replace user-facing `inference-readiness-kit` references with `aipreflight`.
  - Why: the first 30 seconds of reading must tell a coherent story.
  - Done when: README opens with the new name and the broader production readiness promise.

- [x] Keep compatibility notes for the old name.
  - What: add one short note that this project was formerly `inference-readiness-kit`.
  - Why: old blog posts, resumes, and links may still mention the old name.
  - Done when: old readers understand they are in the right place.

- [ ] Update generated media only after the README story is stable.
  - What: regenerate thumbnail, demo captions, and any screenshots that show the old name.
  - Why: visuals should not be polished before the product scope is settled.
  - Done when: `docs/thumbnail.png`, `demo/demo.gif`, and screenshots use `aipreflight`.

## CLI shape

- [x] Add a real `aipreflight` CLI entrypoint.
  - What: expose commands through Python packaging, for example:

    ```bash
    aipreflight check --profile profiles/inference.yml
    aipreflight check --profile profiles/rag.yml
    aipreflight report runs/latest
    aipreflight diagnose runs/latest
    ```

  - Why: a named CLI makes the project feel like a product, not a folder of scripts.
  - Done when: the current shell scripts can still work, but the primary README path uses `aipreflight`.

- [x] Keep existing scripts as wrappers during migration.
  - What: make `scripts/gate.sh`, `scripts/sweep.sh`, and existing Python scripts call the new CLI or share its internal modules.
  - Why: this avoids breaking the working demo while the project is renamed.
  - Done when: old commands still pass tests and README uses the new commands.

- [x] Standardize exit codes.
  - What:
    - `0` means readiness pass.
    - `1` means readiness fail.
    - `2` means invalid config or missing dependency.
    - `3` means probe/eval execution error.
  - Why: CI/CD systems need predictable behavior.
  - Done when: tests cover the exit code contract.

## Profiles

- [x] Add `profiles/inference.yml`.
  - What: current vLLM and OpenAI-compatible endpoint readiness checks.
  - Why: this preserves the current strongest proof: latency, TTFT, throughput, errors, and Prometheus diagnosis.
  - Done when: it can reproduce the current gate behavior.

- [x] Add `profiles/app.yml`.
  - What: generic AI application readiness checks for teams using hosted APIs.
  - Why: this makes the project relevant to companies that do not run their own inference infrastructure.
  - Checks:
    - smoke test endpoint
    - eval suite present
    - cost budget configured
    - logs/traces/metrics endpoint configured
    - deployment gate configured
    - rollback/runbook link present
  - Done when: a simple API-backed AI app can be checked without self-hosted inference.

- [ ] Add `profiles/rag.yml`.
  - What: RAG-specific checks.
  - Why: RAG is one of the most common AI productionization use cases and shows business relevance.
  - Checks:
    - retrieval quality eval
    - answer quality eval
    - hallucination or citation check
    - empty retrieval handling
    - latency and cost budget
    - observability fields for query, retrieved docs, model, prompt version
  - Done when: a RAG demo can fail readiness for poor retrieval even if the server is healthy.

- [x] Add schema validation for profiles.
  - What: validate required fields and print actionable config errors.
  - Why: readiness tools lose trust if they silently ignore missing config.
  - Done when: invalid profile files fail with exit code `2` and a clear message.

## llmprobe integration

- [x] Treat `llmprobe` as the external runtime probe adapter.
  - What: call `llmprobe` from `aipreflight` for endpoint checks.
  - Why: external probes are the cleanest way to measure what users experience.
  - Done when: `aipreflight check --profile profiles/inference.yml` runs `llmprobe` and stores its JSONL output.

- [x] Create a stable adapter contract for probe outputs.
  - What: define the fields `aipreflight` expects from `llmprobe` JSONL.
  - Why: the flagship should not break whenever `llmprobe` output evolves.
  - Done when: tests load fixture JSONL and validate parsing.

- [x] Keep `llmprobe` optional outside inference profiles.
  - What: `profiles/app.yml` should not require `llmprobe` unless endpoint probing is configured.
  - Why: hosted-API teams may start with app-level smoke tests and evals.
  - Done when: app profile works without a local `llmprobe` install.

## Dependency installation (deferred)

Status as of Phase 2: not built. The current behavior is good enough for now.
`llmprobe` is a separate Go binary, so it cannot be a Python dependency in
`pyproject.toml`. We document `go install github.com/Jwrede/llmprobe@latest` as a
manual prerequisite, and `aipreflight check` already fails fast with exit code 2
and an actionable message when the binary is missing. CI never needs `llmprobe`
because tests run offline through `aipreflight check --probes <fixture>`.

What we would add to smooth onboarding, and why it is deferred:

- [ ] Add `scripts/install-deps.sh` with a no-Go install path.
  - What: detect OS/arch, download the matching prebuilt `llmprobe` release tarball
    from GitHub Releases (assets exist for linux/darwin/windows, amd64/arm64),
    verify against `checksums.txt`, install to `~/.local/bin`, and warn if that dir
    is not on PATH. Fall back to `go install` only for building from source.
  - Why: removes the hard Go-toolchain requirement. A user with only `curl` and
    `tar` (standard on macOS/Linux) can install the probe.
  - Why deferred: the manual `go install` line plus the exit-2 message already
    unblock setup. A download-and-extract script needs checksum verification,
    PATH handling, and a Windows story (`.zip`, not `.tar.gz`) to be trustworthy,
    which is more surface area than Phase 2 needed.
  - Done when: `curl -fsSL .../install-deps.sh | bash` installs a working
    `llmprobe` on macOS/Linux without Go, with checksum verification.

- [ ] Add an `aipreflight doctor` subcommand.
  - What: a read-only environment check (llmprobe present and version-compatible,
    Python version, profiles parse, optional Prometheus reachability) with an
    opt-in `--install` flag that calls `install-deps.sh`.
  - Why: one command tells a new user or CI job what is missing instead of failing
    mid-`check`. Run after `pip install -e .`, during onboarding, in CI before the
    gate job, or when `check` exits 2. NOT run inside every `check` (the hot path
    already validates its own dependencies; coupling a read-only verb to an install
    side effect is wrong).
  - Why deferred: with only `llmprobe` to verify, `doctor` is thin and overlaps the
    existing exit-2 message and the one-liner above. Its value grows in Phase 3-4
    when there are more dependencies to check (tokentoll, eval adapters, telemetry
    endpoints). Build it then so it checks enough to earn its place.
  - Done when: `aipreflight doctor` reports environment readiness, `--install` fixes
    a missing `llmprobe`, and a test covers both paths with `shutil.which` mocked.

- [ ] Add the install one-liner to the README once `install-deps.sh` exists.
  - Why: matches the "zero-friction first experience" goal (curl install and run).
  - Done when: README shows the one-liner alongside the manual `go install` option.

## tokentoll integration

- [x] Treat `tokentoll` as the cost gate adapter.
  - What: call `tokentoll` to estimate token cost for prompts, eval datasets, or representative usage scenarios.
  - Why: cost control is a clear business pain and differentiates the project from generic monitoring.
  - Done when: readiness can fail because expected monthly or per-request cost exceeds the configured budget.

- [x] Add cost budget fields to profiles.
  - What:

    ```yaml
    cost:
      max_cost_per_request_usd: 0.02
      max_monthly_cost_usd: 1000
      expected_requests_per_month: 50000
    ```

  - Why: cost needs an explicit business threshold, not only raw token counts.
  - Done when: report shows estimated cost, budget, and pass/fail reason.

- [x] Keep cost estimates explainable.
  - What: report model, input tokens, output tokens, request volume, and pricing assumption.
  - Why: people will not trust a cost verdict if they cannot see where it came from.
  - Done when: report includes the cost calculation inputs.

## Evals integration

- [ ] Add a simple eval runner interface.
  - What: support a local command that returns JSON results, for example `pytest`, `promptfoo`, `ragas`, or a custom script.
  - Why: quality is the missing layer between "the endpoint is up" and "the AI feature is safe to ship".
  - Done when: a profile can define an eval command and a minimum pass rate.

- [ ] Support quality gates.
  - What: fail readiness when eval pass rate, answer quality, retrieval precision, or regression threshold is below target.
  - Why: production AI should not ship only because infrastructure metrics are green.
  - Done when: reports show quality pass/fail next to latency and cost.

- [ ] Add fixtures for passing and failing eval results.
  - What: create small JSON fixtures for deterministic tests.
  - Why: eval integration must be testable without calling live LLM APIs.
  - Done when: tests cover pass, fail, and malformed eval output.

## Observability checks

- [x] Keep Prometheus support for inference diagnosis.
  - What: preserve current queue, KV cache, GPU, and server-side latency diagnosis.
  - Why: this is already a strong differentiator and should not be diluted.
  - Done when: existing diagnose tests still pass after the rename.

- [x] Add generic OpenTelemetry readiness checks.
  - What: verify that traces/logs/metrics are configured or that required environment variables/endpoints exist.
  - Why: hosted-API applications still need observability even if they do not expose vLLM metrics.
  - Done when: app profile can report missing telemetry config as a readiness warning or failure.

- [x] Define required AI observability fields.
  - What: recommend fields such as request ID, user/team, model, provider, prompt version, token counts, latency, cost, eval version, and error type.
  - Why: teams need debugging and cost attribution after launch.
  - Done when: README has a short observability contract and the app profile can check for it.

## Reporting

- [x] Produce one machine-readable report.
  - What: write `runs/latest/aipreflight-report.json`.
  - Why: CI/CD, dashboards, and future integrations need structured output.
  - Done when: JSON report includes verdict, failed checks, warnings, metrics, thresholds, and artifact paths.

- [x] Produce one human-readable report.
  - What: write `runs/latest/aipreflight-report.md`.
  - Why: recruiters, engineering managers, and teams need to understand the decision quickly.
  - Done when: report has sections for quality, cost, latency, observability, deployment, and recommended action.

- [x] Keep the verdict blunt.
  - What: use `PASS`, `FAIL`, and `WARN`, with a short reason.
  - Why: the tool is valuable because it makes deployment decisions clearer.
  - Done when: the first screen of the report tells the user whether to ship.

## Example projects

- [x] Add a small API-backed AI app example.
  - What: a minimal service that calls an LLM API and has smoke tests, evals, cost budget, and telemetry config.
  - Why: this proves `aipreflight` is not only for self-hosted inference.
  - Done when: `profiles/app.yml` can check it end to end.

- [ ] Add a RAG example.
  - What: a minimal RAG app with a tiny document set, retrieval eval, answer eval, and cost gate.
  - Why: RAG is a common customer problem and makes the portfolio story concrete.
  - Done when: bad retrieval can fail readiness while infrastructure still passes.

- [x] Keep the current vLLM example.
  - What: preserve Kubernetes, Prometheus, Grafana, DCGM, and RunPod setup.
  - Why: this remains the strongest proof for inference infrastructure roles.
  - Done when: the vLLM path is documented as the `inference` profile.

## Documentation

- [ ] Rewrite README around the broader promise.
  - What: lead with "production readiness checks for AI applications and LLM inference endpoints".
  - Why: the first paragraph must match the career positioning.
  - Done when: a hiring manager can understand the project without knowing vLLM.

- [ ] Add "When to use this" section.
  - What: explain prototype-to-production situations:
    - before merging an AI feature
    - before routing traffic to a new model
    - before increasing rollout percentage
    - before approving a customer pilot
  - Why: concrete use cases make the tool feel commercially relevant.
  - Done when: README shows practical trigger points.

- [ ] Add "What this checks" section.
  - What: list evals, latency, cost, observability, deployment config, and runbooks.
  - Why: this maps directly to the positioning.
  - Done when: readers can connect the project to production AI reliability in under one minute.

- [ ] Add "What this does not replace" section.
  - What: say it does not replace LiteLLM, Prometheus, Grafana, OpenTelemetry, promptfoo, Ragas, or Kubernetes.
  - Why: the product boundary must stay credible.
  - Done when: scope is clear and not overclaimed.

- [ ] Update blog and portfolio references after the rename.
  - What: change site, CV, and blog links from `inference-readiness-kit` to `aipreflight`.
  - Why: the flagship story should be consistent everywhere.
  - Done when: website, CV, and project links all use the new name.

## Tests

- [x] Keep current unit tests green during every step.
  - Why: the existing inference gate already works and should not regress.
  - Done when: `pytest` passes after each migration phase.

- [x] Add CLI tests.
  - What: test `aipreflight check`, `aipreflight report`, and invalid config handling.
  - Why: the CLI becomes the primary product surface.
  - Done when: tests verify exit codes and generated artifacts.

- [x] Add profile validation tests.
  - What: valid and invalid profile fixtures.
  - Why: most user errors will be configuration errors.
  - Done when: bad config fails clearly.

- [ ] Add integration tests with fake adapters.
  - What: fake `llmprobe`, fake `tokentoll`, fake eval output, and fake Prometheus response.
  - Why: CI must be deterministic and not require paid APIs or GPUs.
  - Done when: full readiness pass/fail can be tested offline.

## Release sequence

### Phase 1: Rename without behavior changes (DONE)

- [x] Rename repo, package metadata, README title, URLs, and docs references.
- [x] Keep old scripts working.
- [x] Run tests.

Why: establish the new public identity without risking the working inference functionality.

### Phase 2: Add CLI and profiles (DONE)

- [x] Add `aipreflight` CLI.
- [x] Add `profiles/inference.yml`.
- [x] Move current threshold behavior behind the inference profile.
- [x] Generate JSON and Markdown reports from the CLI.

Why: turn the current scripts into a product-shaped tool.

### Phase 3: Add app and cost readiness (DONE)

- [x] Add `profiles/app.yml`.
- [x] Add optional `tokentoll` cost gate.
- [x] Add a hosted-API example app.
- [x] Document app-level readiness checks.

Why: broaden the project beyond teams that host their own inference.

### Phase 4: Add eval and RAG readiness

- [ ] Add eval runner adapter.
- [ ] Add `profiles/rag.yml`.
- [ ] Add RAG example.
- [ ] Add quality gates to the report.

Why: quality gates are the biggest missing piece in the current project.

### Phase 5: Polish as flagship proof

- [ ] Regenerate demo and thumbnail.
- [ ] Write a flagship blog post.
- [ ] Update website and CV project descriptions.
- [ ] Add a short architecture diagram.

Why: the project should clearly prove the AI Platform & Reliability positioning.

## First implementation slice

Do this first:

1. Rename README and metadata to `aipreflight`.
2. Add `profiles/inference.yml` equivalent to the current default behavior.
3. Add `aipreflight check --profile profiles/inference.yml`.
4. Keep `scripts/gate.sh` working as a wrapper.
5. Generate `aipreflight-report.json` and `aipreflight-report.md`.
6. Run tests and update README quick start.

This is the smallest useful step because it changes the public story while preserving the strongest current functionality.

## Success criteria

The project is ready to use as the flagship portfolio proof when:

- A recruiter or hiring manager understands the production AI readiness story from the README alone.
- A technical reviewer can run one command and get a pass/fail verdict.
- The tool checks at least latency, errors, cost, eval quality, and observability readiness.
- `llmprobe` and `tokentoll` are clearly integrated without being merged into this repo.
- The demo works without a GPU for app/RAG checks and still supports GPU-backed inference checks.
- CI runs deterministic tests without paid APIs.
- Website, CV, and blog all describe the same project story.
