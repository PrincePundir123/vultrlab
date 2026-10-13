# Proof-Carrying Browser Operations

PCBO is this project's proposed design, not an established standard.

Definitions are immutable versions. Each contains a hash, trusted contract,
restricted steps, creation time, and attached validation records. Current lifecycle
state and history belong to the operation, not its immutable definition.
Contracts include the allowed origin, input/output schemas, policy revision and a
seven-day validity window. Expired definitions require a newly learned version.

Implemented lifecycle transitions:

`DRAFT → LEARNING → TESTING → ACTIVE`

`ACTIVE → QUARANTINED → REPAIRING → TESTING → ACTIVE`

Failed candidates remain recorded and cannot become active. An old active version
remains auditable but cannot execute while the operation is quarantined. The MVP
does not separately persist every intermediate state named in the original prompt
(for example VERIFIED and SUPERSEDED); validation records and active-version pointers
represent those distinctions.

Read validation cases include on-time, delayed, unknown, missing date and canceled
orders. Held-out inputs are not provided to the discovery prompt. The fixed policy
can only be changed by source-code review, never by the model.

Write candidates require explicit admin review. Approval is per exact request, not
blanket permission for a tool. Approval expires after ten minutes and is consumed
atomically with job creation. Dispatch checks expiry again. A changed version needs
a newly prepared and approved request.
Approval also includes a hash of the exact permission contract.

The independent verifier checks exact persisted fields and evidence presence. The
optional vision observation is recorded separately, with explicit unavailable state.
