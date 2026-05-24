# Editorial Workflow User Guide — DOC-002

This guide covers the human-in-the-loop editorial features introduced in Phases 2–5 of the professional pivot.

## Overview

Alter-Ego supports a 7-phase carousel workflow and a blog post editorial pipeline:

| Content Type | Workflow Phases |
|--------------|-----------------|
| Carousel | Brief → Research → Outline → Content → Design → Images → Final Review → Published |
| Blog Post | Draft → Under Review → Approved → Published (with optional schedule) |

## Getting Started

### 1. Personas

Personas define voice, tone, and forbidden phrases for AI-generated content.

- Navigate to **Dashboard → Personas**
- Create a persona with writing samples and tone attributes
- Assign a persona when starting an editorial workflow or generating blog AI suggestions

After Phase 5 migration, a **Default (Migrated)** persona is available, built from existing carousel outputs.

### 2. Quality Rubrics

Rubrics define scoring criteria (originality, voice match, engagement, clarity).

- Navigate to **Dashboard → Rubrics**
- Use the default rubric or create custom criteria
- Run rubric evaluation from the blog editor or carousel workflow review gates

### 3. Carousel Editorial Workflow

1. Open a carousel project
2. Start the editorial workflow from the workflow panel
3. Review AI output at each phase gate (research, outline, content, design, images)
4. Approve, reject, or edit at each interrupt
5. Track progress on the **Workflow Kanban** board

### 4. Blog Post Editorial Workflow

1. Create or edit a blog post from **Dashboard → Blog Posts**
2. Submit for review — assigns a reviewer and sends a notification
3. Reviewer approves, rejects, or requests changes
4. Publish immediately or schedule with the datetime picker
5. AI disclosure label is required before publish

### 5. Quality Tools (Phase 4)

Available on the blog editor:

- **SEO Preview** — title, meta description, social card preview
- **Accessibility Checker** — alt text and color contrast warnings
- **Editorial Analytics** — content velocity and quality scores on **Dashboard → Analytics**

Keyboard shortcuts (`?` to open help):

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save draft |
| `Ctrl+Enter` | Submit for review |

## Notifications

The notification center (bell icon) shows:

- Review requests and deadline reminders
- Scheduled publish confirmations
- Workflow failure alerts (admins)

## Workflow Kanban & Calendar

- **Kanban** — visual board of carousel projects by workflow phase
- **Calendar** — scheduled blog posts and in-progress content by date

## Admin: Data Migration

After upgrading to Phase 5, run the migration once:

```bash
# Preview
uv run python scripts/migrate_phase5.py --dry-run

# Apply
uv run python scripts/migrate_phase5.py
```

Or via API (admin only):

```
POST /api/admin/migration/phase5?dry_run=false
```

## Feature Flags

Operators can disable features during rollout via environment variables:

| Variable | Default | Controls |
|----------|---------|----------|
| `FEATURE_FLAG_EDITORIAL_WORKFLOW` | `true` | Carousel editorial workflow |
| `FEATURE_FLAG_QUALITY_CHECKS` | `true` | SEO, accessibility, plagiarism |
| `FEATURE_FLAG_WORKFLOW_BOARD` | `true` | Kanban board |
| `FEATURE_FLAG_CONTENT_CALENDAR` | `true` | Content calendar |

When disabled, affected endpoints return HTTP 503.

## Support

For technical debt items and known gaps, see [TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md).
