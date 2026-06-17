# Guide: Suspense-based data loading

Canonical data-loading patterns for the Next.js 16 / React 19 frontend. Implements [ADR-010](../decisions/0010-suspense-data-loading.md).
Complements [`minimizing-useeffect-guide.md`](./minimizing-useeffect-guide.md) (which covers what NOT to do).

**Rule:** never fetch in `useEffect`. Pick one of the three patterns below.

## 1. Server Component for initial data

A route's first data load happens on the server — no client round-trip, streamed HTML.

```tsx
// app/dashboard/knowledge/page.tsx  (Server Component — no "use client")
import { fetchDocuments } from "@/modules/knowledge";

export default async function KnowledgePage() {
  const documents = await fetchDocuments(); // server-side fetch
  return <KnowledgeBaseInterface initialDocuments={documents} />;
}
```

Keep route pages thin: fetch + compose, push interactivity into client components.

## 2. TanStack Query for client-side data

Interactive/refetchable data uses TanStack Query v5 with **co-located query-option factories** exposed via the
module barrel — never a raw `fetch` in a component/effect.

```ts
// modules/knowledge/queries.ts
import { queryOptions } from "@tanstack/react-query";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_ENDPOINTS } from "@/constants/api";

export const knowledgeKeys = { all: ["documents"] as const };

export const documentsOptions = () =>
  queryOptions({
    queryKey: knowledgeKeys.all,
    queryFn: () => authenticatedFetch(API_ENDPOINTS.DOCUMENTS),
  });
```

```tsx
// a client component
"use client";
import { useQuery } from "@tanstack/react-query";
import { documentsOptions } from "@/modules/knowledge";

export function DocumentList() {
  const { data } = useQuery(documentsOptions());
  // ...
}
```

Mutations: `useMutation` + explicit `queryClient.invalidateQueries({ queryKey })`. Never mutate cache via effects.

## 3. React 19 `use()` + `<Suspense>`

Unwrap a promise/resource in a client component and let Suspense render the fallback; pair with an error boundary.

```tsx
"use client";
import { use, Suspense } from "react";

function Profile({ profilePromise }: { profilePromise: Promise<Profile> }) {
  const profile = use(profilePromise); // suspends until resolved
  return <ProfileCard profile={profile} />;
}

export function ProfileSection({ profilePromise }: { profilePromise: Promise<Profile> }) {
  return (
    <ErrorBoundary fallback={<ProfileError />}>
      <Suspense fallback={<ProfileSkeleton />}>
        <Profile profilePromise={profilePromise} />
      </Suspense>
    </ErrorBoundary>
  );
}
```

`useSuspenseQuery` integrates TanStack Query with this model (no `isLoading` branch — the boundary handles it).

## Loading & error state

Express them with **boundaries**, not effect-driven flags:

- Loading → a `<Suspense fallback={...}>` boundary around the consumer.
- Error → an error boundary (`fallback`) around the Suspense boundary.
- No `const [loading, setLoading] = useState(...)` toggled inside a `useEffect`.

## When manual `isLoading` is still acceptable

Suspense governs **data loading** (initial/refetchable reads). It does **not**
replace per-action pending flags. A manual loading flag is fine — and preferred —
for **local mutations / submissions**, because the state is owned by the action,
not by a data dependency the boundary can suspend on:

- `useMutation().isPending` to disable a submit button / show an inline spinner
  (create / update / delete / publish).
- A `const [isSubmitting, setIsSubmitting] = useState(false)` toggled around a
  user-triggered handler (e.g. login submit, "Generate preview" button) that
  isn't a `useQuery`.

These are **class (b)** in the AE-0187 baseline and are NOT migration targets.

```tsx
// ✅ OK — mutation pending flag drives the button, not a data fetch
const createDocument = useCreateDocument();
<NeonButton disabled={createDocument.isPending} onClick={handleSubmit}>
  {createDocument.isPending ? t("saving") : t("save")}
</NeonButton>;
```

What is NOT acceptable is using a manual flag for the **initial data read**:

```tsx
// ❌ NOT acceptable — initial data load via manual flag; use useSuspenseQuery + <Suspense>
const { data, isLoading } = useQuery(documentsOptions());
if (isLoading) return <Skeleton />; // ← move to a <Suspense fallback>
```

## Anti-patterns (rejected — see `minimizing-useeffect-guide.md`)

```tsx
// ❌ NEVER — waterfall, race, duplicated state, untestable; blocked by ESLint no-restricted-syntax
useEffect(() => {
  fetch("/api/documents").then((r) => r.json()).then(setDocs);
}, []);
```

## Ownership

Each bounded-context module owns its query contracts (`modules/<context>` query keys + option factories),
exposed only through the module's public barrel (`@/modules/<context>`) — consistent with ADR-009 and the
Phase 7 module boundaries.
