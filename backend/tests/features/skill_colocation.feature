Feature: Runtime skills resolve from their co-located backend package (AE-0246)

  The runtime skills (carousel-pipeline, carousel-refinement, knowledge-base)
  live inside the backend package at rag_backend/agents/skills/ and resolve
  package-relative, so they ship with `COPY backend/src/` and resolve identically
  in local dev and the built image. Root skills/ is delivery-only. Because merging
  to main auto-deploys prod, a wrong path is a request-time FileNotFoundError.

  Scenario: Every carousel phase skill + shared standard resolves after relocation
    Given the runtime skills are co-located under rag_backend/agents/skills
    When phase_subagents / instruction_context_loader resolve a phase skill
    Then every phase SKILL.md and its _shared standard resolves to an existing file
    And no FileNotFoundError is raised

  Scenario: Resolution is package-relative (works inside the built image)
    Given the backend image is built (skills arrive via COPY backend/src/)
    When get_runtime_skills_filesystem_root() resolves a skill path in the image
    Then it points at /app/src/rag_backend/agents/skills and every path exists

  Scenario: An absolute env override still wins
    Given ALTER_EGO_RUNTIME_SKILLS_ROOT is set to an absolute directory
    When get_runtime_skills_filesystem_root() runs
    Then it returns that override (relative/unset falls back to the package location)

  Scenario: The skill-boundary gate enforces the new layout
    Given the runtime skills are inside the package and root skills/ is delivery-only
    When validate_skill_boundary runs
    Then the runtime skills + required slash commands validate and no error is raised
    And the Dockerfile copies backend/src/ and never copies skills/delivery
