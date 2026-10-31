"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonEntityWorkspace } from "@/components/molecules/neon-entity-workspace";
import { NeonSearchBar } from "@/components/molecules/neon-search-bar";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NEON_RED } from "@/constants/neon";
import { useEntityEditor } from "@/lib/use-entity-editor";
import {
  usePersonas,
  type PersonaCreatePayload,
  type PersonaProfile,
} from "@/modules/persona";
import { CreatePersonaCard } from "@/app/dashboard/personas/create-persona-card";
import { PersonaForm } from "@/app/dashboard/personas/persona-form";
import { PersonaTile } from "@/app/dashboard/personas/persona-tile";
import { PersonasEmptyState } from "@/app/dashboard/personas/personas-empty-state";

const PAGE_FONT_FAMILY = "Inter, system-ui, sans-serif";

/** On a phone, the search box keeps the 44 px minimum touch target. */
const SEARCH_BAR_CLASS = "w-full sm:w-[200px] max-sm:[&_input]:min-h-11";

/** On a phone, every form button and text box keeps a 44 px touch target. */
const FORM_TOUCH_CLASS =
  "max-sm:[&_button]:min-h-11 max-sm:[&_button]:min-w-11 max-sm:[&_input]:min-h-11";

interface PersonaListProps {
  personas: PersonaProfile[];
  searchQuery: string;
  loading: boolean;
  failed: boolean;
  onCreate: () => void;
  onEdit: (persona: PersonaProfile) => void;
  onDelete: (persona: PersonaProfile) => void;
}

function PersonaList(props: Readonly<PersonaListProps>): React.ReactElement {
  const t = useTranslations("personas.page");
  const { personas, searchQuery, onCreate, onEdit, onDelete } = props;
  if (props.loading) {
    return (
      <div className="flex justify-center py-12">
        <NeonSpinner size="lg" />
      </div>
    );
  }
  if (props.failed) {
    return (
      <p role="alert" className="text-center py-8" style={{ color: NEON_RED }}>
        {t("loadError")}
      </p>
    );
  }
  const query = searchQuery.toLowerCase();
  const filtered = personas.filter((p) => p.name.toLowerCase().includes(query));
  if (filtered.length === 0) {
    return <PersonasEmptyState searchQuery={searchQuery} onCreate={onCreate} />;
  }
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
      {filtered.map((persona) => (
        <PersonaTile
          key={persona.id}
          persona={persona}
          onEdit={() => onEdit(persona)}
          onDelete={() => onDelete(persona)}
        />
      ))}
      <CreatePersonaCard onCreate={onCreate} />
    </div>
  );
}

export default function PersonasPage(): React.ReactElement {
  const t = useTranslations("personas.page");
  const tDelete = useTranslations("personas.delete");
  const [searchQuery, setSearchQuery] = useState("");
  const collection = usePersonas();
  const editor = useEntityEditor<PersonaProfile, PersonaCreatePayload>(
    collection,
  );

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: PAGE_FONT_FAMILY }}
    >
      <NeonTopBar
        title={t("title")}
        breadcrumb={[{ label: t("breadcrumb") }]}
        actions={
          editor.showingList && (
            <NeonSearchBar
              placeholder={t("search")}
              value={searchQuery}
              onChange={setSearchQuery}
              className={SEARCH_BAR_CLASS}
            />
          )
        }
      />

      <div className="page-content px-4 py-6 md:px-8">
        <NeonEntityWorkspace
          editor={editor}
          deleteT={tDelete}
          list={
            <PersonaList
              personas={collection.personas}
              searchQuery={searchQuery}
              loading={collection.loading}
              failed={collection.error !== null}
              {...editor.listActions}
            />
          }
          renderForm={(persona) => (
            <div className={FORM_TOUCH_CLASS}>
              <PersonaForm persona={persona} {...editor.formActions} />
            </div>
          )}
        />
      </div>
    </div>
  );
}
