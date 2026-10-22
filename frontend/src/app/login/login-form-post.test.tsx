import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { CreateUserDialog } from "@/components/admin/create-user-dialog";
import { LoginForm } from "./login-form";

const FORM_TAG = /<form\b[^>]*>/;

function formTagOf(markup: string): string {
  return FORM_TAG.exec(markup)?.[0] ?? "";
}

describe("server-rendered password forms", () => {
  // Scenario: The login form is a POST form before hydration
  it("renders the login form as a POST to /auth/login", () => {
    const markup = renderToString(
      <LoginForm
        email=""
        password=""
        error=""
        isLoading={false}
        setEmail={vi.fn()}
        setPassword={vi.fn()}
        handleSubmit={vi.fn()}
      />,
    );

    const form = formTagOf(markup);
    expect(form).toMatch(/\bmethod="post"/);
    expect(form).toMatch(/\baction="\/auth\/login"/);
    expect(markup).toMatch(/name="password"/);
  });

  // Scenario: Every form with a password field posts
  it("renders the create-user form as a POST", () => {
    const markup = renderToString(
      <CreateUserDialog onClose={vi.fn()} onSuccess={vi.fn()} />,
    );

    expect(formTagOf(markup)).toMatch(/\bmethod="post"/);
  });
});
