# Demonstration storyboard

Use real Vultr models for the recorded submission. Test fixtures are not a substitute.

1. Show Northstar's synthetic orders and upload `samples/sample_orders.csv`.
2. In Operation Library, learn the read workflow. Show actual MODEL_PROPOSAL,
   BROWSER_ACTION, screenshot, regression and held-out validation events.
3. Run reusable execution; show delayed, on-track and unknown results.
4. Review the exact write definition. Prepare a request for ORD-102, approve its
   immutable snapshot, submit, and inspect the independently verified receipt.
5. In Reliability Lab, switch to Version 2. Execute the old read definition and show
   quarantine. Repair; show candidate tests and the new immutable version.
6. Turn on the hostile text scenario. Show actual policy rejection if the model tries
   a forbidden action; do not claim it tried one if it did not. Separately run the
   deterministic adversarial policy tests to demonstrate enforcement.
7. Run deadline containment. Show SANDBOX_TERMINATED, cleanup=true and app health.
8. Enable timeout-after-write and demonstrate reconciliation without duplicate writes.

Suggested slides: business problem; PCBO lifecycle; trust boundaries; live workflow;
measured results; failure/recovery; limitations and next steps.

Short description: Reusable supplier-portal browser tools with explicit permission
contracts, exact human approval, independent outcome verification and bounded repair.

Long description: Skeleton Key Guard learns a read-only supplier workflow from actual
browser observations using Vultr inference. A restricted interpreter executes the
workflow in disposable containers. Candidate versions must pass deterministic
regression and held-out checks before reuse. Operators review write definitions and
approve exact delivery-request snapshots. An independent verifier checks persisted
portal records; timeout reconciliation avoids blind retries. Website changes trigger
quarantine and versioned repair. The controlled portal uses only synthetic data.

Submission checklist: public HTTPS app, original MIT repository, setup instructions,
Vultr backend and inference, recorded containment moment, slides, cover, truthful
benchmark data, known limitations, attribution for the general Skeleton Key idea.
