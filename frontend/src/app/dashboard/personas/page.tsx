"use client";

import { useState } from "react";
import { NeonSearchBar } from "@/components/molecules/neon-search-bar";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { PERSONAS } from "@/app/dashboard/personas/constants";
import {
  CreatePersonaCard,
  PersonaCard,
  PersonasEmptyState,
} from "@/app/dashboard/personas/persona-cards";

export default function PersonasPage(): React.ReactElement {
  const [searchQuery, setSearchQuery] = useState("");

  const filtered = PERSONAS.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      <NeonTopBar
        title="Personas"
        breadcrumb={[{ label: "voice profiles" }]}
        actions={
          <NeonSearchBar
            placeholder="Search personas..."
            value={searchQuery}
            onChange={setSearchQuery}
            className="w-[200px]"
          />
        }
      />

      <div className="page-content" style={{ padding: "24px 32px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
            gap: 16,
          }}
        >
          {filtered.map((persona) => (
            <PersonaCard key={persona.name} persona={persona} />
          ))}
          <CreatePersonaCard />
        </div>
        {filtered.length === 0 && (
          <PersonasEmptyState searchQuery={searchQuery} />
        )}
      </div>
    </div>
  );
}
