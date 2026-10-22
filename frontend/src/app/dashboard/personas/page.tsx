"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonConfirmDialog } from "@/components/molecules/neon-confirm-dialog";
import { NeonSearchBar } from "@/components/molecules/neon-search-bar";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NEON_RED } from "@/constants/neon";
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

type View =
  | { kind: "list" }
  | { kind: "create" }
  | { kind: "edit"; persona: PersonaProfile };

const LIST_VIEW: View = { kind: "list" };

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
  const {
    personas,
    loading,
    error,
    create,
    update,
    delete: remove,
  } = usePersonas();
  const [view, setView] = useState<View>(LIST_VIEW);
  const [deleting, setDeleting] = useState<PersonaProfile | null>(null);

  const handleSave = async (payload: PersonaCreatePayload): Promise<void> => {
    if (view.kind === "edit") {
      await update(view.persona.id, payload);
    } else {
      await create(payload);
    }
    setView(LIST_VIEW);
  };

  const handleDelete = async (persona: PersonaProfile): Promise<void> => {
    await remove(persona.id);
    setDeleting(null);
  };

  const editing = view.kind === "edit" ? view.persona : undefined;

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: PAGE_FONT_FAMILY }}
    >
      <NeonTopBar
        title={t("title")}
        breadcrumb={[{ label: t("breadcrumb") }]}
        actions={
          view.kind === "list" && (
            <NeonSearchBar
              placeholder={t("search")}
              value={searchQuery}
              onChange={setSearchQuery}
              className="w-full sm:w-[200px]"
            />
          )
        }
      />

      <div className="page-content px-4 py-6 md:px-8">
        {view.kind === "list" ? (
          <PersonaList
            personas={personas}
            searchQuery={searchQuery}
            loading={loading}
            failed={error !== null}
            onCreate={() => setView({ kind: "create" })}
            onEdit={(persona) => setView({ kind: "edit", persona })}
            onDelete={setDeleting}
          />
        ) : (
          <PersonaForm
            key={editing?.id ?? view.kind}
            persona={editing}
            onSave={handleSave}
            onCancel={() => setView(LIST_VIEW)}
          />
        )}
      </div>

      {deleting && (
        <NeonConfirmDialog
          title={tDelete("title")}
          body={tDelete("body", { name: deleting.name })}
          confirmLabel={tDelete("confirm")}
          cancelLabel={tDelete("cancel")}
          errorFallback={tDelete("error")}
          onConfirm={() => handleDelete(deleting)}
          onClose={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
