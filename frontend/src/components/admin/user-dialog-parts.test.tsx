import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, renderHook, screen, act } from "@/test/utils";
import {
  UserDialogActions,
  UserDialogShell,
  UserRoleSelect,
  useDialogStatus,
} from "./user-dialog-parts";

describe("UserDialogShell", () => {
  it("renders title, subtitle, error and success banners", () => {
    // Scenario: shell shows feedback banners
    render(
      <UserDialogShell
        title="Title"
        subtitle={<p>sub</p>}
        error="boom"
        success="yay"
      >
        <span>body</span>
      </UserDialogShell>,
    );
    expect(screen.getByRole("heading", { name: "Title" })).toBeInTheDocument();
    expect(screen.getByText("sub")).toBeInTheDocument();
    expect(screen.getByText("boom")).toBeInTheDocument();
    expect(screen.getByText("yay")).toBeInTheDocument();
    expect(screen.getByText("body")).toBeInTheDocument();
  });

  it("omits the banners when there is no feedback", () => {
    // Scenario: no feedback banners
    render(
      <UserDialogShell title="Title" error="">
        <span>body</span>
      </UserDialogShell>,
    );
    expect(screen.queryByText("boom")).not.toBeInTheDocument();
    expect(document.querySelectorAll(".mt-4.rounded-md")).toHaveLength(0);
  });
});

describe("UserDialogActions", () => {
  it("renders a submit button and cancels through onClose", () => {
    // Scenario: submit variant
    const onClose = vi.fn();
    render(
      <UserDialogActions
        onClose={onClose}
        isLoading={false}
        label="Save"
        loadingLabel="Saving"
      />,
    );
    expect(screen.getByRole("button", { name: "Save" })).toHaveAttribute(
      "type",
      "submit",
    );
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows the loading label and disables the primary button", () => {
    // Scenario: loading state
    render(
      <UserDialogActions
        onClose={vi.fn()}
        isLoading
        label="Save"
        loadingLabel="Saving"
      />,
    );
    expect(screen.getByRole("button", { name: "Saving" })).toBeDisabled();
  });

  it("renders a confirm button calling onConfirm when provided", () => {
    // Scenario: destructive confirm variant
    const onConfirm = vi.fn();
    render(
      <UserDialogActions
        onClose={vi.fn()}
        isLoading={false}
        label="Delete"
        loadingLabel="Deleting"
        onConfirm={onConfirm}
      />,
    );
    const button = screen.getByRole("button", { name: "Delete" });
    expect(button).toHaveAttribute("type", "button");
    fireEvent.click(button);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});

describe("UserRoleSelect", () => {
  it("reports the chosen role", () => {
    // Scenario: role change
    const onChange = vi.fn();
    render(<UserRoleSelect value="editor" onChange={onChange} />);
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "admin" },
    });
    expect(onChange).toHaveBeenCalledWith("admin");
  });
});

describe("useDialogStatus", () => {
  it("clears feedback and flags loading on begin, releases on finish", () => {
    // Scenario: request lifecycle
    const { result } = renderHook(() => useDialogStatus());
    act(() => {
      result.current.setError("e");
      result.current.setSuccess("s");
    });
    expect(result.current.error).toBe("e");
    expect(result.current.success).toBe("s");
    act(() => result.current.begin());
    expect(result.current).toMatchObject({
      error: "",
      success: "",
      isLoading: true,
    });
    act(() => result.current.finish());
    expect(result.current.isLoading).toBe(false);
  });
});
