/**
 * Document scope in the Knowledge Base: badge, scope filter and the card's
 * scope switch.
 */
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import type { Document } from "@/schemas/knowledge";
import { DocumentCard } from "./document-card";
import { DocumentList } from "./document-list";

function doc(overrides: Partial<Document>): Document {
  return {
    id: "d1",
    title: "Meu currículo",
    status: "completed",
    scope: "personal",
    is_public: false,
    metadata: {},
    chunk_count: 4,
    created_at: "2026-10-22T00:00:00Z",
    updated_at: "2026-10-22T00:00:00Z",
    error_message: null,
    ...overrides,
  };
}

const PERSONAL = doc({ id: "p1", title: "Private notes" });
const PUBLIC = doc({
  id: "q1",
  title: "Public bio",
  scope: "public",
  is_public: true,
});

function renderList(documents: Document[], onChangeScope = vi.fn()): void {
  render(
    <DocumentList
      documents={documents}
      onCreateNew={vi.fn()}
      onUploadNew={vi.fn()}
      onDeleteDocument={vi.fn()}
      onChangeScope={onChangeScope}
    />,
  );
}

function listedTitles(): string[] {
  return screen
    .queryAllByRole("heading", { level: 3 })
    .map((heading) => heading.textContent);
}

function filterBy(label: string): void {
  const group = screen.getByRole("group", { name: en.knowledge.scope.filter });
  fireEvent.click(within(group).getByRole("button", { name: label }));
}

describe("Document scope", () => {
  /** Scenario: Each document shows its scope */
  it("shows a Personal or Public badge from the document scope", () => {
    renderList([PERSONAL, PUBLIC]);
    const cards = screen.getAllByTestId("document-scope");
    expect(cards.map((badge) => badge.textContent)).toEqual([
      en.knowledge.scope.personal,
      en.knowledge.scope.public,
    ]);
    expect(pt.knowledge.scope.personal).toBe("Pessoal");
    expect(pt.knowledge.scope.public).toBe("Público");
  });

  /** Scenario: The list can show only public or only personal knowledge */
  it("filters the list by scope", () => {
    renderList([PERSONAL, PUBLIC]);
    filterBy(en.knowledge.scope.public);
    expect(listedTitles()).toEqual(["Public bio"]);
    filterBy(en.knowledge.scope.personal);
    expect(listedTitles()).toEqual(["Private notes"]);
    filterBy(en.knowledge.scope.all);
    expect(listedTitles()).toEqual(["Private notes", "Public bio"]);
    expect(pt.knowledge.scope.all).toBe("Todos");
  });

  /** Scenario: The list can show only public or only personal knowledge */
  it("marks the active scope filter as pressed", () => {
    renderList([PERSONAL, PUBLIC]);
    filterBy(en.knowledge.scope.public);
    expect(
      screen.getByRole("button", {
        name: en.knowledge.scope.public,
        pressed: true,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: en.knowledge.scope.all,
        pressed: false,
      }),
    ).toBeInTheDocument();
  });

  /** Scenario: The scope filter combines with the search */
  it("combines the scope filter with the search box", () => {
    const other = doc({
      id: "q2",
      title: "Blog export",
      scope: "public",
      is_public: true,
    });
    renderList([PERSONAL, PUBLIC, other]);
    filterBy(en.knowledge.scope.public);
    fireEvent.change(screen.getByPlaceholderText(en.knowledge.search), {
      target: { value: "bio" },
    });
    expect(listedTitles()).toEqual(["Public bio"]);
  });

  /** Scenario: The owner changes a document's scope from its card */
  it("asks to make a personal document public", () => {
    const onChangeScope = vi.fn();
    renderList([PERSONAL], onChangeScope);
    fireEvent.click(
      screen.getByRole("button", { name: en.knowledge.scope.makePublic }),
    );
    expect(onChangeScope).toHaveBeenCalledWith("p1", "public");
    expect(pt.knowledge.scope.makePublic).toBe("Tornar público");
  });

  /** Scenario: The owner changes a document's scope from its card */
  it("asks to make a public document personal", () => {
    const onChangeScope = vi.fn();
    renderList([PUBLIC], onChangeScope);
    fireEvent.click(
      screen.getByRole("button", { name: en.knowledge.scope.makePersonal }),
    );
    expect(onChangeScope).toHaveBeenCalledWith("q1", "personal");
  });

  /** Scenario: The owner changes a document's scope from its card */
  it("disables the switch while the change is in flight and says when it failed", () => {
    render(
      <DocumentCard
        document={PERSONAL}
        onChangeScope={vi.fn()}
        changingScope
        scopeChangeFailed
      />,
    );
    expect(
      screen.getByRole("button", { name: en.knowledge.scope.changing }),
    ).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      en.knowledge.scope.changeFailed,
    );
  });

  /** Scenario: Each document shows its scope */
  it("shows the badge without a switch when the card has no scope handler", () => {
    render(<DocumentCard document={PUBLIC} />);
    expect(screen.getByTestId("document-scope")).toHaveTextContent(
      en.knowledge.scope.public,
    );
    expect(
      screen.queryByRole("button", { name: en.knowledge.scope.makePersonal }),
    ).not.toBeInTheDocument();
  });

  /** Scenario: A system document shows its scope without a switch */
  it("shows a system badge and no switch for a system scope", () => {
    render(
      <DocumentCard
        document={doc({ scope: "internal" })}
        onChangeScope={vi.fn()}
      />,
    );
    expect(screen.getByTestId("document-scope")).toHaveTextContent(
      en.knowledge.scope.system,
    );
    expect(pt.knowledge.scope.system).toBe("Sistema");
    expect(
      screen.queryByRole("button", { name: en.knowledge.scope.makePublic }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: en.knowledge.scope.makePersonal }),
    ).not.toBeInTheDocument();
  });

  /** Scenario: A system document shows its scope without a switch */
  it("lists a system document only under All", () => {
    const system = doc({
      id: "s1",
      title: "Carousel source",
      scope: "carousel",
    });
    renderList([PERSONAL, PUBLIC, system]);
    filterBy(en.knowledge.scope.personal);
    expect(listedTitles()).toEqual(["Private notes"]);
    filterBy(en.knowledge.scope.public);
    expect(listedTitles()).toEqual(["Public bio"]);
    filterBy(en.knowledge.scope.all);
    expect(listedTitles()).toEqual([
      "Private notes",
      "Public bio",
      "Carousel source",
    ]);
  });

  /** Scenario: A failed scope change says so on its document only */
  it("marks only the cards whose ids are changing or failed", () => {
    render(
      <DocumentList
        documents={[PERSONAL, PUBLIC]}
        onCreateNew={vi.fn()}
        onUploadNew={vi.fn()}
        onDeleteDocument={vi.fn()}
        onChangeScope={vi.fn()}
        changingScopeIds={new Set(["q1"])}
        scopeChangeFailedIds={new Set(["p1"])}
      />,
    );
    expect(
      screen.getByRole("button", { name: en.knowledge.scope.makePublic }),
    ).toBeEnabled();
    expect(
      screen.getByRole("button", { name: en.knowledge.scope.changing }),
    ).toBeDisabled();
    expect(screen.getAllByRole("alert")).toHaveLength(1);
  });
});
