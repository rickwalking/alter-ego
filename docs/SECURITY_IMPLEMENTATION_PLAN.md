# Alter-Ego Security & Admin Panel Implementation Plan

## Executive Summary

This document outlines the complete security hardening plan for Alter-Ego, implementing authentication, RBAC with Admin/Editor roles, admin-panel-only user management, and visitor restrictions.

---

## 1. Role Model

| Role | Description |
|------|-------------|
| **Admin** | Full system access. Creates, edits, deletes users. Accesses all resources regardless of ownership. Exclusive access to `/admin` routes. |
| **Editor** | Creates, edits, deletes **own** carousels, documents, and conversations. Can trigger generation pipelines and publish to Instagram. No access to Admin Panel. |
| **Visitor** *(unauthenticated)* | Reads public blog posts. Chats with the LLM via **ephemeral anonymous sessions** (no DB persistence). **Blocked** from all document, carousel, creation, and admin features. |

---

## 2. Permission Matrix

### 2.1 Auth & Admin
| Endpoint | Visitor | Editor | Admin |
|----------|---------|--------|-------|
| `POST /api/auth/token` | ✅ | ✅ | ✅ |
| `POST /api/auth/change-password` | ❌ 401 | ✅ self | ✅ self |
| `GET /api/auth/me` | ❌ 401 | ✅ | ✅ |
| `GET /api/admin/users` | ❌ 403 | ❌ 403 | ✅ |
| `POST /api/admin/users` | ❌ 403 | ❌ 403 | ✅ |
| `PATCH /api/admin/users/{id}` | ❌ 403 | ❌ 403 | ✅ |
| `DELETE /api/admin/users/{id}` | ❌ 403 | ❌ 403 | ✅ |
| `POST /api/admin/users/{id}/reset-password` | ❌ 403 | ❌ 403 | ✅ |

### 2.2 Documents — Visitor Blocked
| Endpoint | Visitor | Editor | Admin |
|----------|---------|--------|-------|
| All document endpoints | ❌ 403 | ✅ own | ✅ any |

### 2.3 Carousels
| Endpoint | Visitor | Editor | Admin |
|----------|---------|--------|-------|
| All mutations | ❌ 403 | ✅ own | ✅ any |
| `GET /api/carousels/{id}/blog` | ✅ **PUBLIC** | ✅ **PUBLIC** | ✅ **PUBLIC** |
| Image serving endpoints | ✅ **PUBLIC** | ✅ **PUBLIC** | ✅ **PUBLIC** |

### 2.4 Conversations
| Endpoint | Visitor | Editor | Admin |
|----------|---------|--------|-------|
| `POST /api/conversations` | ✅ (anon) | ✅ | ✅ |
| All other endpoints | ❌ 403 | ✅ own | ✅ any |

### 2.5 Search
| Endpoint | Visitor | Editor | Admin |
|----------|---------|--------|-------|
| All search endpoints | ❌ 403 | ✅ | ✅ |

### 2.6 WebSocket
| Endpoint | Visitor | Editor | Admin |
|----------|---------|--------|-------|
| `/ws/chat/{conversation_id}` | ✅ (anon token) | ✅ | ✅ |

---

## 3. Anonymous Visitor Flow

```
Visitor opens /chat
  └── Frontend detects no auth cookie
      └── Calls POST /api/conversations (no auth header)
          └── Backend creates ephemeral conversation in Redis (TTL 24h)
              └── Returns { conversation_id, anonymous_token }
                  └── Frontend stores anonymous_token in memory
                      └── WebSocket connects with ?token=<anonymous_token>
                          └── Backend validates token: accepts if valid & matches convo_id
```

- Anonymous tokens use separate `ANON_SECRET_KEY` with `type: "anon"` claim
- Anonymous tokens expire in **1 hour**
- Redis key: `anon_chat:{conversation_id}` with TTL

---

## 4. Backend Security Measures

### 4.1 Dependencies
- `get_current_user` — validates JWT from Bearer header or cookie
- `get_current_user_optional` — returns None for public endpoints
- `require_admin` — 403 if not admin
- `require_editor_or_admin` — 403 if not editor/admin
- `require_owner_or_admin` — resource-level authorization

### 4.2 Rate Limiting
| Endpoint | Limit |
|----------|-------|
| `POST /api/auth/token` | 5 req/min/IP |
| `POST /api/admin/users` | 10 req/min/admin |
| `POST /api/documents/upload` | 20 req/hour/user |
| `POST /api/carousels` | 20 req/hour/user |
| `POST /api/carousels/{id}/generate` | 10 req/hour/user |
| Anonymous `POST /api/conversations` | 10 req/hour/IP |

### 4.3 Secret Hardening
- `SECRET_KEY` — main JWT secret, env-only, rotated quarterly
- `ANON_SECRET_KEY` — anonymous JWT secret, env-only
- Remove hardcoded default from `settings.py`, raise `ValueError` if missing
- `.env` and `.env.local` in `.gitignore`

### 4.4 WebSocket Security
- Extract `?token=` from query params
- Validate JWT on connection
- For anonymous tokens: verify `type == "anon"` and `conversation_id` match
- For authenticated: verify ownership or admin role
- Reject with code `1008` on any failure

---

## 5. Frontend Architecture

### 5.1 Authentication Flow
- JWT returned in **HttpOnly, Secure, SameSite=Strict** cookie
- `credentials: "include"` on all API calls
- Next.js `middleware.ts` for route guards

### 5.2 Middleware
```typescript
// Route classification
const PUBLIC_ROUTES = ["/", "/blog", "/blog/[id]", "/login"];
const ADMIN_ROUTES = ["/admin", "/admin/users"];
const EDITOR_ROUTES = ["/create", "/create/[id]", "/create/[id]/publish", "/knowledge"];
```

### 5.3 Auth Context & Hooks
- `use-auth.ts` — returns user, isLoading, isAdmin, isEditor
- `use-require-auth.ts` — client-side role checking
- `ProtectedRoute` component

---

## 6. Admin Panel Design

### 6.1 Routes
- `/admin` → redirects to `/admin/users`
- `/admin/users` → user management page

### 6.2 Components
| Component | Responsibility |
|-----------|---------------|
| `AdminLayout` | Sidebar + header, admin-only access check |
| `UsersPage` | Server component, fetches users |
| `UserTable` | Displays users with columns |
| `CreateUserDialog` | Modal form for new users |
| `EditUserDialog` | Modal to change role/status |
| `DeleteUserDialog` | Confirmation with self-deletion prevention |
| `ChangePasswordDialog` | Admin resets user password |
| `RoleBadge` | Admin (red), Editor (blue) |

### 6.3 Security UI Measures
- Self-deletion disabled with tooltip
- Last-admin protection (backend + frontend)
- Generated password shown once with copy button
- Audit trail: Created At, Last Login At

---

## 7. Database Schema

### 7.1 New Tables
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'editor' CHECK (role IN ('admin', 'editor')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

### 7.2 Alterations
- Add `owner_id UUID REFERENCES users(id)` to: `documents`, `conversations`, `carousel_projects`
- Add `is_public BOOLEAN DEFAULT false` to `carousel_projects`
- Leave `owner_id` nullable on `conversations` to support anonymous chat

### 7.3 Migration Sequence
1. `001_create_users_table`
2. `002_add_owner_columns`
3. Bootstrap admin via CLI
4. `003_backfill_ownership`
5. `004_add_not_null_constraints`

---

## 8. API Endpoints

### 8.1 Auth
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/token` | None | Login, sets cookie |
| POST | `/api/auth/change-password` | Auth | Change own password |
| GET | `/api/auth/me` | Auth | Get current user |

### 8.2 Admin
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/admin/users` | Admin | List all users |
| POST | `/api/admin/users` | Admin | Create user |
| PATCH | `/api/admin/users/{id}` | Admin | Update role/status |
| DELETE | `/api/admin/users/{id}` | Admin | Delete user |
| POST | `/api/admin/users/{id}/reset-password` | Admin | Reset password |

### 8.3 Business Rules
- Last-admin guard: prevent demotion/deletion of last admin → `409`
- Self-deletion guard: users cannot delete themselves → `409`
- Password generation: if omitted, generate secure 16-char password
- Bootstrap: one-time CLI only, fails if admin already exists

---

## 9. Gherkin Scenarios

### 9.1 Authentication
```gherkin
Feature: Authentication
  Scenario: Successful login returns JWT cookie
  Scenario: Invalid credentials rejected
  Scenario: Protected endpoint without auth fails
  Scenario: Change own password
```

### 9.2 RBAC
```gherkin
Feature: Role-Based Access Control
  Scenario: Admin can list all users
  Scenario: Editor cannot access admin endpoints
  Scenario: Visitor cannot upload documents
  Scenario: Visitor cannot create carousels
  Scenario: Visitor can read public blog
  Scenario: Editor can delete own carousel
  Scenario: Editor cannot delete another user's carousel
```

### 9.3 Admin Management
```gherkin
Feature: Admin User Management
  Scenario: Admin creates a new user
  Scenario: Admin creates user with specific password
  Scenario: Admin updates user role
  Scenario: Admin cannot demote last admin
  Scenario: Admin deletes a user
  Scenario: Admin cannot delete themselves
  Scenario: Admin cannot delete last admin
  Scenario: Admin resets user password
```

### 9.4 Anonymous Chat
```gherkin
Feature: Anonymous Visitor Chat
  Scenario: Visitor starts an anonymous conversation
  Scenario: Visitor connects to WebSocket with anonymous token
  Scenario: Visitor cannot access conversation list
  Scenario: Anonymous token expires
```

### 9.5 Frontend Guards
```gherkin
Feature: Frontend Authentication and Route Guards
  Scenario: Unauthenticated user redirected from dashboard
  Scenario: Unauthenticated user can read public blog
  Scenario: Editor cannot access admin panel
  Scenario: Admin sees user management
  Scenario: Admin creates user through UI
```

---

## 10. Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Foundation | 2-3 days | User model, migrations, auth token, bootstrap CLI, SECRET_KEY hardening |
| Phase 2: RBAC & Lockdown | 2-3 days | Auth wired to all routes, ownership checks, public exceptions |
| Phase 3: Anonymous Chat | 1 day | Ephemeral conversations, Redis, anonymous JWT, WebSocket auth |
| Phase 4: Frontend Auth | 2-3 days | Login page, cookies, middleware, AuthContext, API client updates |
| Phase 5: Admin Panel | 2-3 days | /admin/users page, all admin components, TanStack Query hooks |
| Phase 6: Hardening | 2 days | Rate limiting, CORS, CSP, brute-force protection |
| Phase 7: Testing | 2-3 days | Unit tests (>90%), Gherkin scenarios, E2E tests |

---

## 11. New & Modified Files

### Backend
```
backend/src/rag_backend/
├── domain/
│   ├── models.py                 # + User, Role enum
│   └── repositories.py           # + UserRepository protocol
├── infrastructure/
│   ├── auth.py                   # MODIFY
│   ├── config/settings.py        # MODIFY
│   └── database/
│       ├── models.py             # MODIFY
│       └── repositories/user_repository.py  # NEW
├── api/
│   ├── middleware/auth.py        # MODIFY
│   ├── dependencies.py           # NEW
│   ├── routes/
│   │   ├── auth.py               # MODIFY
│   │   ├── admin.py              # NEW
│   │   ├── documents.py          # MODIFY
│   │   ├── carousels.py          # MODIFY
│   │   ├── conversations.py      # MODIFY
│   │   └── search.py             # MODIFY
│   └── app.py                    # MODIFY
└── tests/features/
    ├── auth.feature
    ├── rbac.feature
    ├── admin.feature
    └── anonymous_chat.feature
```

### Frontend
```
frontend/src/
├── app/
│   ├── (admin)/admin/
│   │   ├── layout.tsx
│   │   └── users/page.tsx
│   └── login/page.tsx
├── components/admin/
│   ├── user-table.tsx
│   ├── user-table-row.tsx
│   ├── create-user-dialog.tsx
│   ├── edit-user-dialog.tsx
│   ├── delete-user-dialog.tsx
│   ├── change-password-dialog.tsx
│   ├── role-badge.tsx
│   └── admin-header.tsx
├── hooks/
│   ├── use-auth.ts
│   └── use-require-auth.ts
├── lib/
│   ├── api-client.ts             # MODIFY
│   └── server-fetch.ts           # MODIFY
└── middleware.ts                 # NEW
```

---

*Plan created for Alter-Ego Security Hardening. Ready for implementation.*
