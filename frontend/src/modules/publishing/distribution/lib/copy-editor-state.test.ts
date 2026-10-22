import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api-client";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import {
  copySaveErrorKey,
  dirtyFields,
  rebaseDrafts,
  savedCopyTexts,
  toCopyPayload,
} from "./copy-editor-state";

const SAVED = { caption: "c", linkedinPt: "pt", linkedinEn: "en" };

function apiError(detail: unknown): ApiError {
  const error = new ApiError(409, "Conflict");
  error.detail = detail;
  return error;
}

describe("copy editor state", () => {
  it("reads missing texts as empty ones", () => {
    const project = {
      caption: null,
      linkedin_post_pt: undefined,
      linkedin_post_en: "en",
    } as unknown as CarouselProjectResponse;
    expect(savedCopyTexts(project)).toEqual({
      caption: "",
      linkedinPt: "",
      linkedinEn: "en",
    });
  });

  // Scenario: A refreshed project keeps the edits that were not saved
  it("keeps edited drafts and takes the new saved text elsewhere", () => {
    const draft = { ...SAVED, caption: "edited" };
    const newSaved = { caption: "c", linkedinPt: "pt saved", linkedinEn: "en" };
    expect(rebaseDrafts(draft, SAVED, newSaved)).toEqual({
      caption: "edited",
      linkedinPt: "pt saved",
      linkedinEn: "en",
    });
  });

  // Scenario: Saving a LinkedIn post sends only the edited languages
  it("lists only the edited fields among those asked", () => {
    const draft = { caption: "x", linkedinPt: "y", linkedinEn: "en" };
    expect(dirtyFields(draft, SAVED)).toEqual(["caption", "linkedinPt"]);
    expect(dirtyFields(draft, SAVED, ["linkedinPt", "linkedinEn"])).toEqual([
      "linkedinPt",
    ]);
  });

  // Scenario: Saving a LinkedIn post sends only the edited languages
  it("builds the snake_case body of the saved fields", () => {
    const draft = { caption: "x", linkedinPt: "y", linkedinEn: "z" };
    expect(toCopyPayload(draft, ["linkedinPt", "linkedinEn"])).toEqual({
      linkedin_post_pt: "y",
      linkedin_post_en: "z",
    });
    expect(toCopyPayload(draft, ["caption"])).toEqual({ caption: "x" });
  });

  // Scenario: A refused save explains why
  it.each([
    ["version_conflict", "copy.errors.stale"],
    ["caption_published", "copy.errors.captionPublished"],
    ["resume_already_in_progress", "copy.errors.runInProgress"],
    ["something_else", "copy.errors.save"],
  ])("maps the refusal %s to %s", (detail, key) => {
    expect(copySaveErrorKey(apiError(detail))).toBe(key);
  });

  // Scenario: A refused save explains why
  it("falls back to the generic message without a string detail", () => {
    expect(copySaveErrorKey(apiError([{ msg: "too long" }]))).toBe(
      "copy.errors.save",
    );
    expect(copySaveErrorKey(new Error("network"))).toBe("copy.errors.save");
  });
});
