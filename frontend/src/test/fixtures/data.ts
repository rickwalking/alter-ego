// Test fixtures for consistent mock data

export const mockUser = {
  id: "1",
  name: "John Doe",
  email: "john@example.com",
  avatar: "https://example.com/avatar.jpg",
  createdAt: "2024-01-01T00:00:00Z",
};

export const mockMessage = {
  id: "1",
  role: "user" as const,
  content: "Hello, can you tell me about yourself?",
  timestamp: new Date().toISOString(),
};

export const mockAssistantMessage = {
  id: "2",
  role: "assistant" as const,
  content: "Hi! I'm an AI assistant. I can help you learn more about the knowledge base.",
  timestamp: new Date().toISOString(),
};

export const mockDocument = {
  id: "1",
  title: "About Me",
  content: "This is a document about my background, experience, and interests.",
  tags: ["personal", "intro"],
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
};

// Factory functions for creating variations
export function createMessage(overrides: Partial<typeof mockMessage> = {}) {
  return {
    ...mockMessage,
    id: Math.random().toString(36).substring(2, 9),
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

export function createDocument(overrides: Partial<typeof mockDocument> = {}) {
  return {
    ...mockDocument,
    id: Math.random().toString(36).substring(2, 9),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}
