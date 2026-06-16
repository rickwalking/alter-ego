import { describe, it, expect } from "vitest";
import { mapPersonaToCardProps } from "@/modules/editorial-operations/board/personas/adapters/persona-adapter";

describe("mapPersonaToCardProps", () => {
  it("maps persona fields to NeonPersonaCard props", () => {
    const result = mapPersonaToCardProps({
      name: "Pedro",
      role: "Engineer",
      description: "Builds RAG systems",
      skills: ["Python", "React"],
      avatarUrl: "/avatar.png",
    });

    expect(result).toEqual({
      name: "Pedro",
      role: "Engineer",
      description: "Builds RAG systems",
      skills: ["Python", "React"],
      avatarUrl: "/avatar.png",
    });
  });
});
