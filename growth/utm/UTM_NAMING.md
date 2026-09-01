# UTM Naming

Canonical example:

`/radar5?utm_source=meta&utm_medium=paid_social&utm_campaign=sr_prop_test_v1&utm_content=r5_a_feed&proposition=radar5`

Rules:

- lowercase ASCII and underscores;
- campaign stable for the experiment;
- content identifies concept + format;
- proposition is exactly `radar5`, `breakout` or `risk`;
- do not reuse an old `utm_content` after materially changing creative/copy;
- persist first-touch and last-touch separately in production. The local MVP stores the latest observed UTM only.

