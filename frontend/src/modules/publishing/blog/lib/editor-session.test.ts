import { describe, expect, it } from "vitest";
import { blogPost, SEC_1, v2Document } from "../editor.test-utils";
import { updateSection } from "./editor-document";
import {
  ownBumpRetry,
  sessionAfterSave,
  sessionAfterSlot,
  sessionFromPost,
} from "./editor-session";

// Scenarios: tests/features/blog_editor_ae0424.feature (concurrent save
// conflict, section editing) + AE-0424 review (no lost keystrokes/paid slots)

const typed = (title: string) => {
  const session = sessionFromPost(blogPost());
  return { ...session, draft: { ...session.draft!, title } };
};

describe("sessionAfterSave", () => {
  it("takes the saved post when nothing changed during the PUT", () => {
    const prev = typed("Enviado");
    const next = sessionAfterSave(
      prev,
      blogPost({ title: "Enviado", lock_version: 3 }),
      prev.draft,
    );
    expect(next.draft?.title).toBe("Enviado");
    expect(next.base.lock_version).toBe(3);
  });

  it("keeps keystrokes typed while the PUT was in flight", () => {
    const sent = typed("Enviado").draft;
    const prev = typed("Enviado e mais");
    const next = sessionAfterSave(
      prev,
      blogPost({ title: "Enviado", lock_version: 3 }),
      sent,
    );
    expect(next.draft?.title).toBe("Enviado e mais");
    expect(next.original?.title).toBe("Enviado");
  });

  it("takes the server session for a legacy (non-v2) answer or no draft", () => {
    const legacy = blogPost({ content: { markdown: "x" } });
    expect(sessionAfterSave(typed("x"), legacy, null).draft).toBeNull();
    expect(sessionAfterSave(null, blogPost(), null).draft?.title).toBe(
      "GPT 5.6 saiu",
    );
  });
});

describe("sessionAfterSlot", () => {
  it("merges only the slot and keeps other edits", () => {
    const prev = typed("Digitando");
    const server = blogPost({
      lock_version: 3,
      content: updateSection(v2Document(), "pt", {
        id: SEC_1,
        patch: { body_md: "Servidor" },
      }),
    });
    const next = sessionAfterSlot(prev, server, (draft, serverDoc) => ({
      ...draft,
      sections: serverDoc.sections,
    }));
    expect(next.draft?.title).toBe("Digitando");
    expect(next.draft?.document.sections[0]!.body_md).toBe("Servidor");
    expect(sessionAfterSlot(null, server, (d) => d).draft?.title).toBe(
      "GPT 5.6 saiu",
    );
  });
});

describe("ownBumpRetry", () => {
  it("retries on top of a lock our own slot write produced", () => {
    const latest = { ...typed("Novo"), base: blogPost({ lock_version: 5 }) };
    const retry = ownBumpRetry(2, latest);
    expect(retry?.lockVersion).toBe(5);
    expect(retry?.payload).toEqual({ title: "Novo" });
  });

  it("does not retry a conflict from another session", () => {
    expect(ownBumpRetry(2, typed("Novo"))).toBeNull();
    expect(ownBumpRetry(2, null)).toBeNull();
    const legacy = sessionFromPost(
      blogPost({ content: { markdown: "x" }, lock_version: 9 }),
    );
    expect(ownBumpRetry(2, legacy)).toBeNull();
  });
});
