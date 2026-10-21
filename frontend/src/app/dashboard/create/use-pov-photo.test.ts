import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { usePovPhoto } from "./use-pov-photo";

// Gherkin: backend/tests/features/carousel_pov_layouts.feature (AE-0376)
const state = {
  photos: [] as { id: string; created_at: string }[],
  upload: vi.fn(),
};

vi.mock("@/modules/editorial", () => ({
  useCreatorPhotos: () => ({ data: state.photos }),
  useUploadCreatorPhoto: () => ({
    mutate: state.upload,
    isPending: false,
    isError: false,
  }),
}));

describe("usePovPhoto", () => {
  beforeEach(() => {
    state.photos = [];
    state.upload.mockReset();
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
});
