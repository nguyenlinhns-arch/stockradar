# V7.9 Self-Maintenance C2/C3 — hardening addendum

Date: 2026-09-09
Status: current implementation guidance
Base: V7.9 B3 Self-Maintenance / ApprovalStore / TrustedUpdate design

## Purpose

C1 patch analysis is not enough. C2 `maintenance_build_test` and C3 `maintenance_promote` must become the proven bridge from review-only ChatGPT diffs to safe executable candidates without creating a generic remote developer shell.

Reuse existing ApprovalStore and TrustedUpdate. Do not create parallel approval crypto or a second promoter.

## Approval A must bind the whole build transaction

Approval A arguments must include, directly or through one immutable proposal digest:

- `proposal_id`;
- exact `patch_sha256`;
- exact `base_manifest_sha256`;
- exact changed-file list/risk classification digest;
- exact trusted build recipe id + SHA-256;
- exact offline toolchain manifest SHA-256;
- exact guardian-test bundle SHA-256;
- requested candidate version where version is part of the patch/release plan.

If the build recipe/toolchain/guardian suite changes after approval, the approval is invalid. Do not let a caller select arbitrary command/argv/script after approval.

## TOCTOU-safe source snapshot

Immediately before applying the patch:

1. re-hash the patch and exact base files from the proposal;
2. reject if any base/source identity changed;
3. copy only the approved source tree into a new owned candidate root without following symlinks/junctions/reparse points;
4. hash the copied base files again and compare to proposal base manifest;
5. only then apply the exact approved diff to the candidate copy.

Do not treat a pre-copy source hash as sufficient because source could change between validation and copy.

The snapshotter itself is trusted/current-release code, not candidate code.

## Reparse/link policy

Candidate snapshot/apply/extract must reject path escapes through:

- symlink;
- junction;
- mount point;
- Windows reparse point;
- ADS/device path;
- absolute/UNC/parent traversal;
- case-normalization collision.

Do not recursively follow an unexpected reparse point while copying the source tree.

## Fixed sandbox execution

After Approval A, the trusted helper launches only the fixed maintenance recipe inside the existing reviewed isolation model:

- fixed AppContainer profile/SID or equivalently reviewed restricted token;
- no network capabilities;
- Job Object `KILL_ON_JOB_CLOSE` and bounded process/memory/runtime;
- synthetic candidate data root;
- production DPAPI/vault/config/journal/approval files unavailable;
- user-site Python modules disabled;
- package-manager restore/network access disabled;
- fixed offline toolchain/cache paths only;
- no shell command supplied by ChatGPT/caller.

A fresh isolation probe runs immediately before candidate code. If isolation probe fails, build does not start.

## Trusted guardian tests

Candidate-owned tests are useful but cannot be the only acceptance authority because the patch itself may modify tests.

C2 runs two layers:

### Candidate tests
The exact fixed test commands for the candidate tree/package.

### Guardian tests
An immutable test bundle from the CURRENT trusted release/maintenance helper, hash-bound into Approval A. Guardian tests specifically cover invariants a candidate must not self-waive, including:

- protected-path rules;
- no generic shell/raw executor;
- ApprovalStore mismatch/expiry/reuse/consume rules;
- maintenance cannot run inside `execute_task`;
- caller cannot supply executable/build argv/update URL/package/source root;
- journal/dedupe/lease/outcome-unknown rules;
- update package validation + rollback contract;
- semantic security invariants;
- candidate cannot read production secret/vault fixtures;
- sandbox network probe remains blocked.

A candidate may add stronger tests but cannot edit the guardian bundle used to accept itself.

## Evidence authority

Candidate scripts may emit test output, but trusted outer helper owns the evidence envelope.

Outer helper records:

- proposal/build transaction id;
- exact source snapshot manifest SHA;
- post-patch tree manifest SHA;
- toolchain/recipe/guardian SHA;
- sandbox identity/probe result;
- exact trusted fixed stage names;
- each process exit status + bounded stdout/stderr hash;
- package SHA/size;
- candidate release inventory/catalog/version hashes;
- start/end times and resource-bound outcome;
- final PASS/FAIL computed by trusted outer helper.

Candidate code cannot simply write `PASS=true` and become promotable.

## Build failure / crash semantics

Build/test has no authority to alter live runtime.

On crash/power loss/helper failure:

- candidate transaction becomes `FAILED` or `ABANDONED`;
- no automatic promotion;
- do not reuse consumed/expired Approval A for a fresh build transaction;
- preserve bounded evidence/diagnostics;
- orphan candidate roots are inert and garbage-collected later through a trusted bounded cleanup path.

Never infer PASS from the existence of a ZIP.

## Candidate immutability

On C2 PASS:

- finalize candidate directory/package/evidence;
- compute manifest hashes from trusted helper;
- close all build handles;
- make candidate root non-writable to ordinary remote PC tools/current agent policy where practical;
- record immutable candidate identity;
- any file/hash change afterward makes C3 reject.

## Approval B binds exact promotion object

Separate Approval B arguments include at least:

- `candidate_id`;
- `proposal_id`;
- `patch_sha256`;
- `package_sha256` + exact package size;
- `evidence_sha256`;
- candidate version;
- candidate catalog/release inventory identity;
- risk classification summary/digest.

Approval A receipt can never satisfy Approval B.

C3 consumes Approval B only for the exact candidate identity.

## Promotion path

`pc.maintenance_promote` never receives an arbitrary filesystem package path.

Flow:

1. resolve candidate ID inside trusted candidate registry/root;
2. re-hash immutable evidence/package/release inventory;
3. verify C2 PASS from trusted evidence;
4. consume exact Approval B;
5. call `TrustedUpdate.ApplyLocalCandidate(candidateId)`;
6. existing updater owns backup -> stop -> switch -> start -> MCP/health smoke -> commit OR automatic rollback.

Do not duplicate this transaction in maintenance_service.py.

## Trust-boundary risk display

Proposal risk flags should explicitly identify changes touching, for example:

- ApprovalStore;
- TrustedUpdate/updater/launcher/watchdog;
- maintenance service/helper/sandbox;
- protocol/security/semantic authorization;
- cloud auth/device identity;
- protected path logic;
- release inventory/build recipe.

The local approval UI already displays action/args; include a bounded human-readable risk summary/digest in the approved arguments/evidence so high-risk maintenance is not visually indistinguishable from a small adapter optimization.

Risk classification does not replace approval or tests.

## C2/C3 acceptance additions

1. Modify build recipe after Approval A -> reject.
2. Modify guardian bundle/toolchain manifest after Approval A -> reject.
3. Modify source between analyze and snapshot -> reject.
4. Modify source during snapshot -> copied manifest mismatch -> reject.
5. Source/candidate reparse escape -> reject.
6. Patch deletes/weakens its own candidate tests -> guardian tests still execute independently.
7. Candidate prints fake PASS -> outer evidence remains FAIL when a trusted stage fails.
8. Sandbox can read candidate synthetic data but cannot read production DPAPI/vault/config.
9. Sandbox TCP/DNS/HTTP probe fails closed before candidate execution.
10. Build helper crash leaves live runtime unchanged and candidate non-promotable.
11. Candidate package mutated after C2 -> C3 reject.
12. Approval A reused as B -> reject.
13. Approval B for candidate X used on candidate Y -> reject.
14. Caller package/source/command path injection -> schema/implementation reject.
15. Forced broken candidate goes through same TrustedUpdate path and rolls back automatically.
