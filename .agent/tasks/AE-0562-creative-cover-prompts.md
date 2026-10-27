# AE-0562 — More creative cover prompt suggestions

Status: Review
Tier: T1
Priority: High
Type: Bug
Area: Fullstack
Owner: Claude
Branch: fix/ae-0562-creative-cover-prompts
Created: 2026-10-27
Updated: 2026-10-27

## Goal

Pedro (2026-10-27): "suggestion of prompts to create images should have more creativity ... images related to the carousel theme, but with different backgrounds, clothes, positions. The current solution is generating very identical photos."

## Problem

The six curated suggestions (AE-0509/AE-0547) shared one template: framing + "fundo liso #0b0b14" / palette name / hex accent + light + the tail "com um elemento que remeta a <title>". Image models ignore hex codes and the quoted title adds nothing visual, so every result was the same dark studio, black T-shirt, crossed arms. The "Mais ideias" LLM prompt only asked to "vary the angle, background and mood".

## Research (distilled)

Sources: [fal.ai GPT Image 2 prompting guide](https://fal.ai/learn/tools/prompting-gpt-image-2), [nanoprompts GPT Image 2 portrait handbook](https://nanoprompts.org/gpt-image-2/prompt-handbook/portrait), [Quest Studio realistic portrait prompts](https://queststudio.io/blog/chatgpt-image-prompts-realistic-portraits), [LocalLens personal branding photography guide](https://locallens.com/hire-a-photographer-personal-branding-photography/), [Abby Murphy: plan a brand photoshoot](https://abbymurphyphoto.com/how-to-plan-a-brand-photoshoot/), [Mandy Liz: branding shot list](https://mandyliz.com/2022/12/23/planning-a-personal-branding-photoshoot-brand-photography-shot-list-tips/).

1. Photoreal images come from concrete, named details (place, lamp, lens), not abstract style words.
2. Prompt formula: subject + setting + wardrobe + pose/expression + lighting + camera/lens + background.
3. Lens language: 85mm for close portraits, 35–50mm for environmental shots.
4. Environmental portraits (coworking, coffee shop, street, rooftop, park, bookshop) beat plain backdrops for personal brands.
5. Variety per set: different outfits (jackets, layers) and locations; "not enough variety in settings or outfits" is the most common mistake.
6. Action poses (walking, writing, laughing, pointing, holding coffee) read as candid and trustworthy.
7. Light and time of day (golden hour, blue hour, overcast, window, neon, backlight) change the mood more than colour codes.
8. Props tied to the brand/topic tell the story; leave negative space for headlines/banners.

## Acceptance Criteria

- [x] AC1 The curated catalogue builds six suggestions from five pools of eight options (shot/angle, pose, wardrobe, location, light) plus a six-prop theme pool; no two suggestions share an option of any dimension.
- [x] AC2 Colours are named in words from the palette (`colourName`), never hex; no topic quote; theme tie-in via a prop picked from topic keywords (ai, code, money, social, career, general).
- [x] AC3 Deterministic per carousel id (publish step passes the project id; the create wizard seeds with the topic); "Outras ideias" shuffles client-side with no AI call. 400-char cap; pt/en.
- [x] AC4 "Mais ideias" uses prompt v2 (v1 kept): distinct location, wardrobe, pose, angle and light per idea, props/metaphors, colour words, no title text, no personal data; answer objects carry the scene fields.
- [x] AC5 Server-side diversity check: an idea repeating an earlier one's location+pose is dropped, hex-code ideas are dropped; too few left falls into the existing single retry (no extra loops).

## Gherkin

- `frontend/tests/features/cover-prompt-variety-ae0562.feature`
- `backend/tests/features/cover_prompt_variety_ae0562.feature`

## QA Checklist

- [x] Catalogue tests: pairwise distinct, no hex, deterministic, shuffle, theme prop, 400 cap.
- [x] Prompt snapshot asserts the diversity rules; diversity check with fake outputs; no paid API calls.
- [ ] CI green on the PR.
