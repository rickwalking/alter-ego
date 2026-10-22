import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/lib/api-client";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import { PublishPanel } from "./publish-panel";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const CAPTION_LABEL = "instagram.captionLabel";
const LINKEDIN_LABEL = "linkedin.postLabel";

function buildProject(
  overrides?: Partial<CarouselProjectResponse>,
): CarouselProjectResponse {
  return {
    id: "proj-1",
    topic: "Topic",
    title: "Title",
    status: "completed",
    caption: "Saved caption",
    linkedin_post_pt: "Post PT",
    linkedin_post_en: "Post EN",
    design_tokens: { images: { slides: ["/a.jpg"] } },
    created_at: "2026-10-22T00:00:00Z",
    updated_at: "2026-10-22T00:00:00Z",
    ...overrides,
  } as CarouselProjectResponse;
}

async function editCaption(text: string): Promise<void> {
  const user = userEvent.setup();
  const textarea = screen.getByLabelText(CAPTION_LABEL);
  await user.clear(textarea);
  await user.type(textarea, text);
}

describe("PublishPanel copy save (AE-0492)", () => {
  // Scenario: Saving the edited caption sends it with the loaded lock version
  it("saves the edited caption and says it is saved", async () => {
    const user = userEvent.setup();
    const onSaveCopy = vi.fn().mockResolvedValue(undefined);
    render(<PublishPanel project={buildProject()} onSaveCopy={onSaveCopy} />);
    expect(screen.getByRole("button", { name: "copy.save" })).toBeDisabled();
    await editCaption("New caption");
    expect(screen.getByRole("status")).toHaveTextContent("copy.unsaved");
    await user.click(screen.getByRole("button", { name: "copy.save" }));
    expect(onSaveCopy).toHaveBeenCalledWith({ caption: "New caption" });
    expect(screen.getByRole("status")).toHaveTextContent("copy.saved");
    expect(screen.getByRole("button", { name: "copy.save" })).toBeDisabled();
  });

  // Scenario: Copy and publish wait for the edit to be saved
  it("disables copy and publish until the caption is saved", async () => {
    const user = userEvent.setup();
    const onPublish = vi.fn().mockResolvedValue(undefined);
    render(
      <PublishPanel
        project={buildProject()}
        onSaveCopy={vi.fn().mockResolvedValue(undefined)}
        onPublishInstagram={onPublish}
      />,
    );
    await editCaption("Edited caption");
    const publish = screen.getByRole("button", {
      name: "instagram.publishNow",
    });
    expect(publish).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "instagram.copyCaption" }),
    ).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "copy.save" }));
    expect(publish).toBeEnabled();
    await user.click(publish);
    expect(onPublish).toHaveBeenCalledWith("Edited caption");
  });

  // Scenario: Saving a LinkedIn post sends only the edited languages
  it("saves only the edited LinkedIn language", async () => {
    const user = userEvent.setup();
    const onSaveCopy = vi.fn().mockResolvedValue(undefined);
    render(<PublishPanel project={buildProject()} onSaveCopy={onSaveCopy} />);
    await user.click(screen.getByRole("tab", { name: "tabs.linkedin" }));
    const textarea = screen.getByLabelText(LINKEDIN_LABEL);
    await user.type(textarea, " edited");
    expect(
      screen.getByRole("button", { name: "linkedin.copyPost" }),
    ).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "copy.save" }));
    expect(onSaveCopy).toHaveBeenCalledWith({
      linkedin_post_pt: "Post PT edited",
    });
    expect(
      screen.getByRole("button", { name: "linkedin.copyPost" }),
    ).toBeEnabled();
  });

  // Scenario: A refreshed project keeps the edits that were not saved
  it("keeps an unsaved caption when the project is refetched", async () => {
    const onSaveCopy = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(
      <PublishPanel project={buildProject()} onSaveCopy={onSaveCopy} />,
    );
    await editCaption("Draft caption");
    rerender(
      <PublishPanel
        project={buildProject({ linkedin_post_pt: "Saved elsewhere" })}
        onSaveCopy={onSaveCopy}
      />,
    );
    expect(screen.getByLabelText(CAPTION_LABEL)).toHaveValue("Draft caption");
  });

  // Scenario: A refused save explains why
  it("shows why a save was refused and keeps the text", async () => {
    const user = userEvent.setup();
    const refusal = new ApiError(409, "Conflict");
    refusal.detail = "caption_published";
    const onSaveCopy = vi.fn().mockRejectedValue(refusal);
    render(<PublishPanel project={buildProject()} onSaveCopy={onSaveCopy} />);
    await editCaption("Late caption");
    await user.click(screen.getByRole("button", { name: "copy.save" }));
    expect(screen.getByRole("status")).toHaveTextContent(
      "copy.errors.captionPublished",
    );
    expect(screen.getByLabelText(CAPTION_LABEL)).toHaveValue("Late caption");
  });

  // Scenario: A refused save explains why
  it("does not offer a save bar when saving is not wired", () => {
    render(<PublishPanel project={buildProject()} />);
    expect(screen.queryByRole("button", { name: "copy.save" })).toBeNull();
  });

  // Scenario: A refused save explains why
  it("disables save while the caption breaks the Instagram limit", async () => {
    render(
      <PublishPanel
        project={buildProject()}
        onSaveCopy={vi.fn().mockResolvedValue(undefined)}
      />,
    );
    await editCaption(Array.from({ length: 31 }, (_, i) => `#t${i}`).join(" "));
    expect(screen.getByRole("button", { name: "copy.save" })).toBeDisabled();
  });
});

describe("PublishPanel leave guard (AE-0492)", () => {
  function renderWithLink(onFollow: () => void): void {
    render(
      <>
        <a
          href="/dashboard"
          onClick={(event) => {
            event.preventDefault();
            onFollow();
          }}
        >
          Dashboard
        </a>
        <PublishPanel
          project={buildProject()}
          onSaveCopy={vi.fn().mockResolvedValue(undefined)}
        />
      </>,
    );
  }

  // Scenario: Leaving with unsaved edits asks first in the page's own dialog
  it("follows links freely when nothing is unsaved", async () => {
    const user = userEvent.setup();
    const onFollow = vi.fn();
    renderWithLink(onFollow);
    await user.click(screen.getByRole("link", { name: "Dashboard" }));
    expect(onFollow).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  // Scenario: Leaving with unsaved edits asks first in the page's own dialog
  it("holds the link in a styled dialog and stays on keep editing", async () => {
    const user = userEvent.setup();
    const onFollow = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm");
    renderWithLink(onFollow);
    await editCaption("Unsaved");
    await user.click(screen.getByRole("link", { name: "Dashboard" }));
    expect(onFollow).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toHaveTextContent("copy.leave.title");
    expect(confirmSpy).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "copy.leave.cancel" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(onFollow).not.toHaveBeenCalled();
    expect(screen.getByLabelText(CAPTION_LABEL)).toHaveValue("Unsaved");
  });

  // Scenario: Leaving with unsaved edits asks first in the page's own dialog
  it("follows the held link on discard and leave", async () => {
    const user = userEvent.setup();
    const onFollow = vi.fn();
    renderWithLink(onFollow);
    await editCaption("Unsaved");
    await user.click(screen.getByRole("link", { name: "Dashboard" }));
    await user.click(
      screen.getByRole("button", { name: "copy.leave.confirm" }),
    );
    expect(onFollow).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  // Scenario: Leaving with unsaved edits asks first in the page's own dialog
  it("blocks the tab close prompt only while there are unsaved edits", async () => {
    renderWithLink(vi.fn());
    const clean = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(clean);
    expect(clean.defaultPrevented).toBe(false);
    await editCaption("Unsaved");
    const dirty = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(dirty);
    expect(dirty.defaultPrevented).toBe(true);
  });

  // Scenario: Leaving with unsaved edits asks first in the page's own dialog
  it("lets links that open a new tab through", async () => {
    const user = userEvent.setup();
    render(
      <PublishPanel
        project={buildProject()}
        onSaveCopy={vi.fn().mockResolvedValue(undefined)}
      />,
    );
    await editCaption("Unsaved");
    await user.click(screen.getByRole("link", { name: /downloadPdf/ }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
