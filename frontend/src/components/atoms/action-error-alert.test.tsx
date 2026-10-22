import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ActionErrorAlert } from "./action-error-alert";

describe("ActionErrorAlert", () => {
  it("shows the message as an alert", () => {
    // Scenario: A failed create is shown on the personas and rubrics pages
    render(<ActionErrorAlert message="Failed to create persona" />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Failed to create persona",
    );
  });

  it("renders nothing without a message", () => {
    const { container } = render(<ActionErrorAlert message={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
