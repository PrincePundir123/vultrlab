# Measurement protocol

No performance improvement has been established without a controlled run.

The application records actual inference calls, reported token usage, sandbox
startup/execution timing, cleanup flags, test outcomes, and end-to-end job duration.
The UI labels observed duration as including queue time. It does not convert tokens
to money without verified pricing.

For a publishable comparison:

1. Record VM specification, region, image digests, Chromium version, model IDs and date.
2. Use the same ordered sample CSV and unchanged portal scenario.
3. Run at least ten baseline and ten reusable trials, interleaving the modes.
4. Record the initial learning and validation cost separately and include it in
   cumulative cost as reuse count increases.
5. Use identical verification and evidence rules in both modes.
6. Report all failures, sample sizes, median and p95, not only successful fast runs.
7. Export raw jobs/events. Separate synthetic-provider tests from real Vultr trials.

Current baseline discovers once per batch; reusable mode reuses a prior validated
operation. This is not a per-order rediscovery benchmark. Compare equal batch sizes.
Container startup is included in both paths. Vision availability must be reported.

See `verification-report.md` for checks actually executed in this workspace.

## Observed Docker acceptance run

`acceptance-measurements.json` records a real PostgreSQL/API/worker/Chromium/portal
acceptance run using an explicitly deterministic TEST_FIXTURE_NOT_AI provider.
Observed durations: learning and validation 28.854 s; three-order read 8.936 s;
approved submission and verification 3.351 s; expected layout-change detection
7.723 s; repair and validation 29.581 s; three-order read after repair 10.005 s;
deadline containment 8.828 s. Sample size is one per step, not a comparative benchmark.
These timings do not measure Vultr model latency or establish an AI speedup.
