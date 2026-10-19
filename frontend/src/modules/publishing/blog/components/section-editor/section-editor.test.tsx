import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { image, SEC_1, SEC_2, v2Document } from "../../editor.test-utils";
import { BlogSectionEditor } from "./blog-section-editor";
import { ImageSlot } from "./image-slot";
import { LanguageTabs } from "./language-tabs";
import { MigrationBanner } from "./migration-banner";
import type { BlogSectionEditorProps } from "./types";

// Scenarios: tests/features/blog_editor_ae0424.feature (section editing,
// images, cover, PT/EN buttons, migration banner, localized copy)

const IDLE = { pending: false, error: null };

function props(
  overrides: Partial<BlogSectionEditorProps> = {},
): BlogSectionEditorProps {
  return {
    document: v2Document(),
    language: "pt",
    validation: {},
    statusOf: () => IDLE,
    onLanguageChange: vi.fn(),
    onDocumentChange: vi.fn(),
    onGenerateImage: vi.fn(),
    onRewrite: vi.fn(),
    onGenerateTranslation: vi.fn(),
    onSelectText: vi.fn(),
    ...overrides,
  };
}

function lastEdit(
  onDocumentChange: BlogSectionEditorProps["onDocumentChange"],
) {
  const edit = vi.mocked(onDocumentChange).mock.calls.at(-1)?.[0];
  return edit ? edit(v2Document()) : null;
}

describe("BlogSectionEditor", () => {
  // Scenario: Editing a section heading and body persists it
  it("renders one card per section and edits heading/body", () => {
    const p = props();
    render(<BlogSectionEditor {...p} />);
    expect(screen.getAllByText(/^Section \d$/)).toHaveLength(3);
    fireEvent.change(screen.getAllByLabelText("Heading")[0], {
      target: { value: "Novo" },
    });
    expect(lastEdit(p.onDocumentChange)?.sections[0].heading).toBe("Novo");
    fireEvent.change(screen.getAllByLabelText("Body (markdown)")[1], {
      target: { value: "B" },
    });
    expect(lastEdit(p.onDocumentChange)?.sections[1].body_md).toBe("B");
  });

  // Scenario: Adding / Deleting / Reordering sections
  it("adds, deletes and reorders sections", () => {
    const p = props();
    render(<BlogSectionEditor {...p} />);
    fireEvent.click(screen.getByRole("button", { name: "Add section" }));
    expect(lastEdit(p.onDocumentChange)?.sections).toHaveLength(4);
    fireEvent.click(
      screen.getAllByRole("button", { name: "Delete section" })[1],
    );
    expect(
      lastEdit(p.onDocumentChange)?.sections.map((s) => s.id),
    ).not.toContain(SEC_2);
    fireEvent.click(screen.getAllByRole("button", { name: "Move down" })[0]);
    expect(lastEdit(p.onDocumentChange)?.sections[1].id).toBe(SEC_1);
    fireEvent.click(screen.getAllByRole("button", { name: "Move up" })[1]);
    expect(lastEdit(p.onDocumentChange)?.sections[0].id).toBe(SEC_2);
    expect(
      screen.getAllByRole("button", { name: "Move up" })[0],
    ).toBeDisabled();
  });

  // Scenario: Rewrite this section in my voice replaces only that section
  it("asks to rewrite one section and reports text selections", () => {
    const p = props();
    render(<BlogSectionEditor {...p} />);
    fireEvent.click(
      screen.getAllByRole("button", {
        name: "Rewrite this section in my voice",
      })[1],
    );
    expect(p.onRewrite).toHaveBeenCalledWith(SEC_2);
    const body = screen.getAllByLabelText(
      "Body (markdown)",
    )[0] as HTMLTextAreaElement;
    body.setSelectionRange(0, 5);
    fireEvent.select(body);
    expect(p.onSelectText).toHaveBeenCalledWith({
      sectionId: SEC_1,
      text: "Corpo",
    });
  });

  // Scenario: Generating a section image / The cover can be generated
  it("generates the cover and a section image", () => {
    const p = props();
    render(<BlogSectionEditor {...p} />);
    fireEvent.click(
      screen.getAllByRole("button", { name: "Generate image" })[0],
    );
    expect(p.onGenerateImage).toHaveBeenCalledWith(
      { language: "pt", sectionId: null },
      null,
    );
    fireEvent.click(screen.getAllByRole("button", { name: "Regenerate" })[0]);
    expect(p.onGenerateImage).toHaveBeenLastCalledWith(
      { language: "pt", sectionId: SEC_1 },
      "Um farol",
    );
  });

  // Scenario: Removing a section image clears the slot / cover removed
  it("removes an image and edits alt + caption locally", () => {
    const p = props();
    render(<BlogSectionEditor {...p} />);
    fireEvent.click(screen.getAllByRole("button", { name: "Remove image" })[0]);
    expect(lastEdit(p.onDocumentChange)?.sections[0].image).toBeNull();
    fireEvent.change(screen.getAllByLabelText("Alt text")[0], {
      target: { value: "Gráfico de custos" },
    });
    expect(lastEdit(p.onDocumentChange)?.sections[0].image?.alt).toBe(
      "Gráfico de custos",
    );
    fireEvent.change(screen.getAllByLabelText("Caption")[0], {
      target: { value: "" },
    });
    expect(lastEdit(p.onDocumentChange)?.sections[0].image?.caption).toBeNull();
  });

  // Scenario: An empty alt is rejected / heading issues shown
  it("shows document issues on the right section", () => {
    render(
      <BlogSectionEditor
        {...props({
          validation: {
            [`pt:${SEC_1}`]: "altRequired",
            [`pt:${SEC_2}`]: "headingInvalid",
          },
        })}
      />,
    );
    expect(
      screen.getByText("Alt text is required for every image."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Headings cannot start with # or exceed 200 characters.",
      ),
    ).toBeInTheDocument();
  });

  // Scenario: A missing EN translation is read-only with a generate action
  it("is read-only on EN without a translation and offers to generate it", () => {
    const p = props({ language: "en" });
    render(<BlogSectionEditor {...p} />);
    expect(screen.getByText(/no English version yet/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add section" })).toBeDisabled();
    fireEvent.click(
      screen.getByRole("button", { name: "Generate EN translation" }),
    );
    expect(p.onGenerateTranslation).toHaveBeenCalled();
  });

  // Scenario: PT/EN buttons switch the edited document
  it("shows the EN sections and switches language", () => {
    const p = props({ document: v2Document(true), language: "en" });
    render(<BlogSectionEditor {...p} />);
    expect(screen.getByDisplayValue("Body one")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Corpo um")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "EN" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    fireEvent.click(screen.getByRole("button", { name: "PT" }));
    expect(p.onLanguageChange).toHaveBeenCalledWith("pt");
  });
});

describe("ImageSlot", () => {
  // Scenario: A failed image generation shows a visible retry
  it("shows the slot error with a retry and stays editable", () => {
    const onGenerate = vi.fn();
    render(
      <ImageSlot
        slotId="x"
        label="Cover image"
        image={null}
        status={{ pending: false, error: { kind: "ai_failed", detail: null } }}
        readOnly={false}
        issue={null}
        onGenerate={onGenerate}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/Image generation failed/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Image prompt"), {
      target: { value: "  Um farol  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onGenerate).toHaveBeenCalledWith("Um farol");
  });

  it("explains an exhausted image budget", () => {
    render(
      <ImageSlot
        slotId="x"
        label="Cover image"
        image={null}
        status={{ pending: false, error: { kind: "budget", detail: null } }}
        readOnly={false}
        issue={null}
        onGenerate={vi.fn()}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/whole image budget/)).toBeInTheDocument();
  });

  it("disables the controls while generating", () => {
    render(
      <ImageSlot
        slotId="x"
        label="Cover image"
        image={image()}
        status={{ pending: true, error: null }}
        readOnly={false}
        issue={null}
        onGenerate={vi.fn()}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /Regenerate/ })).toBeDisabled();
    expect(screen.getByRole("img", { name: "Arte" })).toBeInTheDocument();
  });
});

describe("LanguageTabs / MigrationBanner", () => {
  it("shows a translation failure", () => {
    render(
      <LanguageTabs
        language="en"
        hasEnglish={false}
        translationStatus={{
          pending: false,
          error: { kind: "ai_failed", detail: null },
        }}
        onChange={vi.fn()}
        onGenerateTranslation={vi.fn()}
      />,
    );
    expect(screen.getByText(/The AI service failed/)).toBeInTheDocument();
  });

  // Scenario: A non-migrated row shows a blocking migration banner
  it("shows the migration banner with the API error", () => {
    render(<MigrationBanner detail="blog_document_not_v2" />);
    expect(screen.getAllByRole("alert")[0]).toHaveTextContent(
      "Migration pending",
    );
    expect(screen.getByText("blog_document_not_v2")).toBeInTheDocument();
  });
});
