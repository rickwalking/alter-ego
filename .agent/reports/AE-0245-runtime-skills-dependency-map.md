# AE-0245 — Runtime-skill → file dependency map (precondition for AE-0246)

**Purpose:** enumerate every consumer of the `skills/runtime/` tree and every
`_shared/` cross-reference so the AE-0246 (RES-8) co-location can update all of
them **in lockstep** and be verified inside the built Docker image — because
merging to `main` auto-deploys prod, a wrong/incomplete move is a request-time
`FileNotFoundError`.

**Status:** audit complete. This is the mandatory input AE-0246 consumes.
Verified against the working tree at branch `chore/agent-restructure-epic-tickets`.

---

## 1. The runtime-skill tree (20 files, a coupled `_shared` tree)

```
skills/runtime/
├── carousel-pipeline/
│   ├── SKILL.md                      # top pipeline skill — references _shared/*.md (8)
│   ├── workflow.md
│   ├── bmad-skill-manifest.yaml
│   ├── contracts/hero_lower_third_v1.yaml
│   ├── phases/{research,outline,content,design,images,final-review}/SKILL.md  # 6 phase skills
│   └── _shared/{critical-rules,anti-patterns,content-contracts,text-formatting,
│               design-system,image-generation,export-and-caption,README}.md   # 8 standards
├── carousel-refinement/SKILL.md
└── knowledge-base/SKILL.md
```

### `_shared/` cross-references (the coupling — must move together)
- **Top** `carousel-pipeline/SKILL.md` references `_shared/<name>.md` (relative, same dir):
  `critical-rules`, `anti-patterns`, `content-contracts`, `text-formatting`,
  `design-system`, `image-generation`, `export-and-caption`.
- **Each phase** `phases/<phase>/SKILL.md` references `../_shared/<name>.md` (one level up):
  e.g. `final-review` → `../_shared/{export-and-caption,content-contracts,critical-rules}.md`;
  `outline` → `../_shared/{critical-rules,text-formatting}.md`; etc.

⇒ Relocating a phase skill **without** preserving the `../_shared/` relative depth
breaks every phase reference. The co-located layout in AE-0246 must keep the
`<pipeline>/phases/<phase>/SKILL.md` ↔ `<pipeline>/_shared/*.md` relative geometry.

---

## 2. The six consumers (each must be updated in lockstep by AE-0246)

| # | Consumer | What it resolves | Exact references to update |
|---|----------|------------------|-----------------------------|
| 1 | `backend/src/rag_backend/domain/constants/runtime_skills.py` | **The path authority.** All other consumers resolve through it. | `DEFAULT_RUNTIME_SKILLS_ROOT = "skills/runtime"`; `RUNTIME_PIPELINE_MARKER = skills/runtime/carousel-pipeline` (repo-root finder); `CAROUSEL_PIPELINE_SKILL_ID = "carousel-pipeline"`; fns `get_runtime_skills_root/_filesystem_root`, `carousel_pipeline_root`, `resolve_runtime_skill_filesystem_path`, `read_runtime_skill_markdown`, `read_runtime_shared_markdown`, `_assert_runtime_path_confined` (path-confinement guard). |
| 2 | `application/services/carousel/phase_subagents.py` | Phase subagent specs. | `SKILL_ROOT = carousel_pipeline_root()`; builds `f"{SKILL_ROOT}/phases/<phase>"` + `f"{SKILL_ROOT}/_shared/*.md"` per phase. |
| 3 | `application/services/carousel/instruction_context_loader.py` | Loads phase skill + shared standards + policy into one instruction string. | imports `read_runtime_skill_markdown`, `read_runtime_shared_markdown`; `_phase_resources()` / `_load(...)`. |
| 4 | `backend/Dockerfile` | **Prod resolution root.** | Line 85 `COPY --chown=fastapi:fastapi skills/runtime/ /app/skills/runtime/`; line 42 `ENV ALTER_EGO_RUNTIME_SKILLS_ROOT=/app/skills/runtime`. Both move when the tree moves. |
| 5 | `scripts/validate_skill_boundary.py` (CI skill-path gate) | Validates runtime dir exists + frontmatter + compatibility links. | `RUNTIME_DIR = SKILLS_DIR / "runtime"`; `RUNTIME_COMPATIBILITY_LINKS = {carousel-pipeline, carousel-refinement, knowledge-base}`; `_validate_runtime_skills()`. |
| 6 | The `_shared/` relative links **inside the markdown** (§1) | Phase ↔ shared standards. | Preserve `_shared/` (top) and `../_shared/` (phase) relative geometry. |

**Resolution order (prod):** `get_runtime_skills_filesystem_root()` reads
`ALTER_EGO_RUNTIME_SKILLS_ROOT` (set to `/app/skills/runtime` in the image), else
falls back to the `DEFAULT_RUNTIME_SKILLS_ROOT` located via `RUNTIME_PIPELINE_MARKER`.
So in prod the env var is authoritative — AE-0246 MUST update the Dockerfile env
to the new co-located path (or set it per-agent).

---

## 3. Finding — repo-root runtime symlinks are PROD-DEAD

`skills/` carries three runtime symlinks: `carousel-pipeline → runtime/carousel-pipeline`,
`carousel-refinement → runtime/carousel-refinement`, `knowledge-base → runtime/knowledge-base`.

Grep evidence (no prod/code consumer):
```
$ rg -n 'skills/(carousel-pipeline|knowledge-base|carousel-refinement)' backend/src scripts | grep -v 'runtime/'
  (no matches)
```
Every code path resolves via `runtime_skills.py` → `skills/runtime/...` (or the
`/app/skills/runtime` env in prod), never via the bare `skills/<id>` symlink.
**⇒ The three runtime-skill symlinks are safe to drop in AE-0246.** (The seven
*delivery* symlinks — `architect-skill`, `developer-skill`, `qa-agent`, etc. — are
a separate concern; they back `/slash-commands` and MUST stay.)

---

## 4. Finding — `/carousel-pipeline` slash-command

No code or `.claude` slash-command was found consuming the runtime symlinks; the
runtime skills are invoked **programmatically** (phase_subagents / instruction
loader), not as user `/slash-commands`. AE-0246 should still grep the user's
`~/.claude` + `.claude/` for a `/carousel-pipeline` command before deleting the
symlink; absent one, no shim is needed.

---

## 5. Pre-existing, UNRELATED gate state (flag for AE-0246 / owner)

`scripts/validate_skill_boundary.py` currently **fails** its unit test
(`backend/tests/unit/scripts/test_validate_skill_boundary.py::test_skill_boundary_validation_passes`)
because commit `04a883b6` ("allow model invocation of delivery skills") removed
`disable-model-invocation: true` from the **delivery** skills, while the validator
still asserts its presence. This is **independent of the runtime-skill relocation**
(it concerns delivery skills, not `skills/runtime/`), predates the agent-restructure
work, lives on the `feat/dev-wave-ae0220-0227` base branch (not on `main`), and
must be resolved by the owner of that policy change (update the validator/test to
the new delivery-skill invocation policy) — NOT by AE-0246.

---

## 6. AE-0246 lockstep checklist (derived from this map)

1. Move `carousel-pipeline/` (incl. `phases/` + `_shared/` with relative geometry),
   `carousel-refinement/`, `knowledge-base/` into their owning agent packages.
2. Update **runtime_skills.py** path constants + `RUNTIME_PIPELINE_MARKER` + the
   repo-root finder to the new location.
3. Update **phase_subagents.py** + **instruction_context_loader.py** (they go
   through runtime_skills.py — confirm no hard-coded `skills/runtime` remains).
4. Update the **Dockerfile** COPY (line 85) + the `ALTER_EGO_RUNTIME_SKILLS_ROOT`
   env (line 42).
5. Update **validate_skill_boundary.py** (`RUNTIME_DIR`, `RUNTIME_COMPATIBILITY_LINKS`).
6. Drop the three prod-dead runtime symlinks + the empty `skills/runtime/`.
7. **Build the image** and assert every phase skill + `_shared` standard resolves
   inside it (not just on the local tree).
