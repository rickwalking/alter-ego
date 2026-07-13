# Carousel presentation policy contracts

Versioned, immutable presentation policies loaded by
`application/services/carousel/presentation_policy.py`.

## Versioning rule

**Never modify an existing policy file.** A behavior change ships a new version
file (`hero_lower_third_vN.yaml`), added to
`SUPPORTED_PRESENTATION_POLICY_VERSIONS`
(`domain/constants/presentation_policy.py`). Old versions stay valid so
in-flight and completed projects keep their frozen semantics.

| Version | Notes |
| ------- | ----- |
| `hero_lower_third_v1` | Baseline. Default for legacy NULL-version rows. |
| `hero_lower_third_v2` | AE-0312: PT casing rules + severity metadata + proper-noun list. Stamped on new carousels at creation. |

## Severity metadata (`rule_severities`, v2+)

Each violation code maps to `blocker` or `warning`. A report blocks approval
only when a blocker-severity violation remains; warnings surface in the review
panel without blocking. The loader asserts every casing rule under `casing.rules`
carries an explicit severity here — a missing tag fails the load (it can never
silently unblock a rule). The code-level default for an absent severity is
`blocker`.

## Proper-noun list (`casing.proper_nouns`, v2+)

**Maintenance ownership: content/editorial.** To enforce a new product or brand
name's canonical casing (e.g. a new model name), add it to
`casing.proper_nouns` in `hero_lower_third_v2.yaml`. This is a policy edit —
**no code deploy is required**. Seeded with `Claude` and `Anthropic`.
Per-project overrides are a non-goal.

## Slide-type exemptions (`casing.rules[].exempt_slide_types`)

A stylistic all-lowercase slide type can opt out of a casing rule by listing its
slide type under that rule's `exempt_slide_types`. An exempted slide produces no
casing violation and receives no casing repair for that rule.
