# `carousel_rubric/` prompt domain

The quality rubric a carousel is generated and scored against: chosen per carousel, criteria in the prompt, scores shown, no automatic rewrite.

## v1

- `content_criteria.yaml`: the rubric's criteria as framed reference data, placed before every content-draft prompt (generic,
  Radar, POV and POV news), so the existing content prompt versions stay unchanged.
- `evaluate.yaml`: the judge prompt that scores each criterion of the drafted carousel on 0-100 and
  answers JSON.
