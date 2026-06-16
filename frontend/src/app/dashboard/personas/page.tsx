"use client";

import { useState } from "react";
import { NeonSearchBar } from "@/components/molecules/neon-search-bar";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NEON_RED } from "@/constants/neon";
import { mapPersonaProfileToCardProps } from "@/modules/editorial-operations";
import { usePersonas } from "@/modules/persona";
import { NeonPersonaCard } from "@/components/organisms/neon-persona-card";
import { CreatePersonaCard } from "@/app/dashboard/personas/create-persona-card";
import { PersonasEmptyState } from "@/app/dashboard/personas/personas-empty-state";

const PAGE_FONT_FAMILY = "Inter, system-ui, sans-serif";

export default function PersonasPage(): React.ReactElement {
  const [searchQuery, setSearchQuery] = useState("");
  const { personas, loading, error, create, refetch } = usePersonas();

  const handleCreatePersona = async (): Promise<void> => {
    const name = window.prompt("Persona name");
    if (!name?.trim()) return;
    await create({
      name: name.trim(),
      expertise_areas: [],
      writing_samples: [],
      forbidden_phrases: [],
      preferred_phrases: [],
    });
    await refetch();
  };

  const filtered = personas.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: PAGE_FONT_FAMILY }}
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
        {loading && (
          <div className="flex justify-center py-12">
            <NeonSpinner size="lg" />
          </div>
        )}
        {error && !loading && (
          <p className="text-center py-8" style={{ color: NEON_RED }}>
            {error}
          </p>
        )}
        {!loading && !error && filtered.length === 0 && (
          <PersonasEmptyState searchQuery={searchQuery} />
        )}
        {!loading && !error && filtered.length > 0 && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
              gap: 16,
            }}
          >
            {filtered.map((persona) => (
              <NeonPersonaCard
                key={persona.id}
                {...mapPersonaProfileToCardProps(persona)}
              />
            ))}
            <CreatePersonaCard onCreate={() => void handleCreatePersona()} />
          </div>
        )}
      </div>
    </div>
  );
}
