# V7.9 update signature fixture

Purpose: cross-language verification of the update-feed v2 canonicalization/signature contract.

This fixture uses a disposable TEST key generated only for verification. The production private publisher key is not present and must never be committed.

Expected values:

- schema: `thaylinh.pc.update-feed.v2`
- key id: `fixture-p256-01`
- curve: ECDSA P-256 / secp256r1
- hash: SHA-256
- signature format: IEEE P1363 fixed field concatenation (`r || s`), exactly 64 bytes before Base64
- canonicalization: recursively sort object property names using ordinal/ASCII order; UTF-8; no whitespace; separators `,` and `:`; signed metadata permits no floating-point values and signed strings/keys are ASCII only
- canonical signed-object SHA-256: `1b3f1d908936c627c7b902d22ca4d67d1fd3b905946c1316d08deb9f3063f8fe`

Acceptance tests for the .NET verifier:

1. The provided envelope verifies with the provided public key.
2. Reformatting/reordering the envelope JSON without changing the `signed` values still verifies because the verifier re-canonicalizes `signed`.
3. Changing any signed field fails verification.
4. Changing `key_id`, schema, signature, or public key fails closed.
5. Duplicate JSON properties, floating-point numbers, non-ASCII signed fields, malformed Base64, or a signature length other than 64 bytes are rejected before update metadata is trusted.
