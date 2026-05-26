import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const handlers = [
  // Health check
  http.get("/api/health", () => {
    return HttpResponse.json({ status: "ok" });
  }),

  // Chat endpoints
  http.post("/api/chat", async ({ request }) => {
    const body = (await request.json()) as { message: string };
    return HttpResponse.json({
      id: Date.now().toString(),
      response: `Response to: ${body.message}`,
      timestamp: new Date().toISOString(),
    });
  }),

  http.get("/api/chat/history", () => {
    return HttpResponse.json([
      {
        id: "1",
        role: "user",
        content: "Hello",
        timestamp: new Date().toISOString(),
      },
      {
        id: "2",
        role: "assistant",
        content: "Hi there! How can I help you today?",
        timestamp: new Date().toISOString(),
      },
    ]);
  }),

  // Knowledge base endpoints
  http.get("/api/knowledge", () => {
    return HttpResponse.json([
      {
        id: "1",
        title: "About Me",
        content: "This is a document about me...",
        tags: ["personal", "intro"],
        createdAt: new Date().toISOString(),
      },
      {
        id: "2",
        title: "My Projects",
        content: "Overview of my projects...",
        tags: ["projects", "work"],
        createdAt: new Date().toISOString(),
      },
    ]);
  }),

  http.post("/api/knowledge", async ({ request }) => {
    const body = (await request.json()) as { title: string; content: string };
    return HttpResponse.json(
      {
        id: Date.now().toString(),
        ...body,
        createdAt: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),
];

export const server = setupServer(...handlers);
