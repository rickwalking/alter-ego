import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConversationSidebar } from "./conversation-sidebar";
import type { Conversation } from "@/schemas/chat";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    className,
  }: {
    children: React.ReactNode;
    href: string;
    className?: string;
  }) => (
    <a href={href} className={className} data-testid={`link-${href}`}>
      {children}
    </a>
  ),
}));

describe("ConversationSidebar Component", () => {
  const mockConversations: Conversation[] = [
    {
      id: "1",
      title: "First Conversation",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: null,
    },
    {
      id: "2",
      title: "Second Conversation",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: null,
    },
    {
      id: "3",
      title: "Third Conversation",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: null,
    },
  ];

  const mockOnNewChat = vi.fn();
  const mockOnSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Given the ConversationSidebar is rendered", () => {
    describe("When the sidebar is displayed", () => {
      it("Then the New Chat button should be visible", () => {
        render(
          <ConversationSidebar
            conversations={mockConversations}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        expect(
          screen.getByRole("button", { name: /new chat/i }),
        ).toBeInTheDocument();
      });

      it("Then all conversations should be listed", () => {
        render(
          <ConversationSidebar
            conversations={mockConversations}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        expect(screen.getByText("First Conversation")).toBeInTheDocument();
        expect(screen.getByText("Second Conversation")).toBeInTheDocument();
        expect(screen.getByText("Third Conversation")).toBeInTheDocument();
      });
    });

    describe("When the New Chat button is clicked", () => {
      it("Then onNewChat should be called", async () => {
        const user = userEvent.setup();
        render(
          <ConversationSidebar
            conversations={mockConversations}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );

        await user.click(screen.getByRole("button", { name: /new chat/i }));
        expect(mockOnNewChat).toHaveBeenCalledTimes(1);
      });
    });

    describe("When conversations are rendered", () => {
      it("Then each conversation should be clickable", () => {
        render(
          <ConversationSidebar
            conversations={mockConversations}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        const buttons = screen.getAllByRole("listitem");
        expect(buttons).toHaveLength(3);
      });

      it("Then each conversation should display a message icon", () => {
        render(
          <ConversationSidebar
            conversations={mockConversations}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        const buttons = screen.getAllByRole("listitem");
        expect(buttons).toHaveLength(3);
      });
    });

    describe("When an active conversation is specified", () => {
      it("Then the active conversation should have active styling", () => {
        render(
          <ConversationSidebar
            conversations={mockConversations}
            activeId="2"
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        const activeButton = screen.getAllByRole("listitem")[1];
        expect(activeButton).toHaveClass("bg-[var(--color-primary)]");
        expect(activeButton).toHaveClass(
          "text-[var(--color-primary-foreground)]",
        );
      });

      it("Then inactive conversations should not have active styling", () => {
        render(
          <ConversationSidebar
            conversations={mockConversations}
            activeId="2"
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        const inactiveButton = screen.getAllByRole("listitem")[0];
        expect(inactiveButton).not.toHaveClass("bg-[var(--color-primary)]");
      });
    });

    describe("When no active conversation is specified", () => {
      it("Then no conversation should have active styling", () => {
        render(
          <ConversationSidebar
            conversations={mockConversations}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        const buttons = screen.getAllByRole("listitem");
        buttons.forEach((button) => {
          expect(button).not.toHaveClass("bg-[var(--color-primary)]");
        });
      });
    });

    describe("When the sidebar has default styling", () => {
      it("Then it should have fixed width", () => {
        const { container } = render(
          <ConversationSidebar
            conversations={mockConversations}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        expect(container.firstChild).toHaveClass("w-64");
      });

      it("Then it should have border on the right", () => {
        const { container } = render(
          <ConversationSidebar
            conversations={mockConversations}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        expect(container.firstChild).toHaveClass("border-r");
      });

      it("Then it should have background color", () => {
        const { container } = render(
          <ConversationSidebar
            conversations={mockConversations}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        expect(container.firstChild).toHaveClass("bg-[var(--color-muted)]");
      });
    });

    describe("When long conversation titles are present", () => {
      it("Then long titles should be truncated", () => {
        const longTitleConversation: Conversation = {
          id: "4",
          title:
            "This is a very long conversation title that should be truncated",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          metadata: null,
        };
        render(
          <ConversationSidebar
            conversations={[longTitleConversation]}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        const titleSpan = screen.getByText(
          longTitleConversation.title as string,
        );
        expect(titleSpan).toHaveClass("truncate");
      });
    });

    describe("When no conversations are provided", () => {
      it("Then the New Chat button should still be visible", () => {
        render(
          <ConversationSidebar
            conversations={[]}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        expect(
          screen.getByRole("button", { name: /new chat/i }),
        ).toBeInTheDocument();
      });

      it("Then no conversation items should be rendered", () => {
        render(
          <ConversationSidebar
            conversations={[]}
            activeId={null}
            onNewChat={mockOnNewChat}
            onSelectConversation={mockOnSelect}
          />,
        );
        expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
      });
    });
  });
});
