# Deprecated — Carousel Pipeline Workflow

> **This file is deprecated as of CP-001 (skills migration).**
> Do not load `workflow.md` into agent context.

## Replacement layout

All content from this file and the legacy monolith `SKILL.md` has been migrated to:

```
skills/carousel-pipeline/
├── SKILL.md                      # Slim routing entry (triggers, phase delegation)
├── _shared/                      # Canonical standards
│   ├── README.md                 # Three-layer alignment (skills → prompts → code)
│   ├── critical-rules.md
│   ├── anti-patterns.md
│   ├── content-contracts.md
│   ├── text-formatting.md
│   ├── design-system.md
│   ├── image-generation.md
│   └── export-and-caption.md
└── phases/
    ├── research/SKILL.md
    ├── outline/SKILL.md
    ├── content/SKILL.md
    ├── design/SKILL.md
    ├── images/SKILL.md
    └── final-review/SKILL.md
```

## Where to find migrated content

| Former section in `workflow.md` | New location |
|--------------------------------|--------------|
| System prompt / input schema | `_shared/critical-rules.md`, `_shared/content-contracts.md` |
| Phase 1: Research | `phases/research/SKILL.md` + `_shared/critical-rules.md` |
| Phase 2: Title optimization | `phases/outline/SKILL.md` + `_shared/text-formatting.md` |
| Phase 3: Content synthesis | `phases/content/SKILL.md` + `_shared/content-contracts.md` |
| Phase 4: Design system | `phases/design/SKILL.md` + `_shared/design-system.md` |
| Phase 5: Image generation | `phases/images/SKILL.md` + `_shared/image-generation.md` |
| Phase 6: Assembly & export | `_shared/export-and-caption.md` |
| Phase 7: Caption generation | `phases/final-review/SKILL.md` + `_shared/export-and-caption.md` |
| Error handling | `_shared/critical-rules.md` |

Git history retains the original monolith. For the authoritative spec, start at [`_shared/README.md`](_shared/README.md).
