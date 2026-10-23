import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { usePovPhoto } from "./use-pov-photo";

/** Gherkin: backend/tests/features/carousel_pov_layouts.feature. */
const state = {
  photos: [] as { id: string; created_at: string }[],
  upload: vi.fn(),
  remove: vi.fn(),
  reset: vi.fn(),
  removeError: null as unknown,
};

vi.mock("@/modules/editorial", () => ({
  useCreatorPhotos: () => ({ data: state.photos }),
  useUploadCreatorPhoto: () => ({
    mutate: state.upload,
    isPending: false,
    isError: false,
  }),
  useDeleteCreatorPhoto: () => ({
    mutate: state.remove,
    reset: state.reset,
    isPending: false,
    isError: state.removeError !== null,
    error: state.removeError,
  }),
  photoInUse: (error: unknown) =>
    error === "in-use"
      ? { carousels: [{ id: "c-1", title: "T" }], topics: [] }
      : null,
}));

describe("usePovPhoto", () => {
  beforeEach(() => {
    state.photos = [];
    state.upload.mockReset();
    state.remove.mockReset();
    state.reset.mockReset();
    state.removeError = null;
  });

  it("preselects the newest photo once", () => {
    const onSelect = vi.fn();
    state.photos = [
      { id: "newest", created_at: "2026-10-15" },
      { id: "older", created_at: "2026-10-01" },
    ];
    const { rerender } = renderHook(() => usePovPhoto("", onSelect));
    expect(onSelect).toHaveBeenCalledWith("newest");
    rerender();
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("keeps an explicit choice", () => {
    const onSelect = vi.fn();
    state.photos = [{ id: "newest", created_at: "x" }];
    renderHook(() => usePovPhoto("mine", onSelect));
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("uploads with the hook role and selects the new photo", () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() => usePovPhoto("", onSelect));
    const file = new File(["x"], "me.png", { type: "image/png" });
    act(() => result.current.section.onUpload(file));
    expect(state.upload).toHaveBeenCalledWith(
      { file, role: "hook" },
      expect.objectContaining({ onSuccess: expect.any(Function) as unknown }),
    );
    const { onSuccess } = state.upload.mock.calls[0]![1] as {
      onSuccess: (photo: { id: string }) => void;
    };
    onSuccess({ id: "uploaded" });
    expect(onSelect).toHaveBeenCalledWith("uploaded");
  });

  /** Scenario: Deleting the selected photo selects the newest remaining one */
  it("selects the newest remaining photo after deleting the selected one", () => {
    const onSelect = vi.fn();
    state.photos = [
      { id: "newest", created_at: "2" },
      { id: "older", created_at: "1" },
    ];
    const { result } = renderHook(() => usePovPhoto("newest", onSelect));
    act(() => result.current.section.onDelete("newest"));
    expect(state.remove).toHaveBeenCalledWith(
      "newest",
      expect.objectContaining({ onSuccess: expect.any(Function) as unknown }),
    );
    const { onSuccess } = state.remove.mock.calls[0]![1] as {
      onSuccess: () => void;
    };
    onSuccess();
    expect(onSelect).toHaveBeenCalledWith("older");
  });

  /** Scenario: Deleting the selected photo selects the newest remaining one */
  it("clears the selection when the last photo is deleted", () => {
    const onSelect = vi.fn();
    state.photos = [{ id: "only", created_at: "1" }];
    const { result } = renderHook(() => usePovPhoto("only", onSelect));
    act(() => result.current.section.onDelete("only"));
    const { onSuccess } = state.remove.mock.calls[0]![1] as {
      onSuccess: () => void;
    };
    onSuccess();
    expect(onSelect).toHaveBeenCalledWith("");
  });

  /** Scenario: Deleting an unused photo after confirming */
  it("keeps the selection when another photo is deleted", () => {
    const onSelect = vi.fn();
    state.photos = [
      { id: "kept", created_at: "2" },
      { id: "other", created_at: "1" },
    ];
    const { result } = renderHook(() => usePovPhoto("kept", onSelect));
    act(() => result.current.section.onDelete("other"));
    const { onSuccess } = state.remove.mock.calls[0]![1] as {
      onSuccess: () => void;
    };
    onSuccess();
    expect(onSelect).not.toHaveBeenCalled();
  });

  /** Scenario: A photo in use lists the carousels that use it */
  it("passes the blocking carousels to the section", () => {
    state.removeError = "in-use";
    const { result } = renderHook(() => usePovPhoto("x", vi.fn()));
    expect(result.current.section.deleteBlockedBy).toEqual({
      carousels: [{ id: "c-1", title: "T" }],
      topics: [],
    });
    expect(result.current.section.deleteFailed).toBe(true);
  });

  /** Scenario: Choosing another photo clears the in-use list */
  it("clears the last delete outcome when the selection changes", () => {
    const { rerender } = renderHook(
      ({ selected }) => usePovPhoto(selected, vi.fn()),
      { initialProps: { selected: "x" } },
    );
    state.reset.mockClear();
    rerender({ selected: "x" });
    expect(state.reset).not.toHaveBeenCalled();
    rerender({ selected: "y" });
    expect(state.reset).toHaveBeenCalledTimes(1);
  });
});
