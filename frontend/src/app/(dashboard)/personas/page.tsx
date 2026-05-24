"use client";

import { useState } from "react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Textarea,
  Badge,
  Alert,
  AlertDescription,
  Spinner,
} from "@/components/ui";
import { usePersonas } from "@/features/persona/hooks/use-personas";
import type { PersonaProfile, PersonaCreatePayload } from "@/features/persona/types";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-yellow-500",
  active: "bg-green-500",
  archived: "bg-gray-500",
};

export default function PersonasPage() {
  const { personas, loading, error, refetch, create, update, delete: deletePersona } = usePersonas();
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<PersonaCreatePayload>({
    name: "",
    description: "",
    tone_attributes: {
      formal: 0.3,
      conversational: 0.8,
      humorous: 0.4,
    },
    writing_samples: [],
    forbidden_phrases: [],
    preferred_phrases: [],
    expertise_areas: [],
  });

  const handleCreate = async () => {
    try {
      await create(formData);
      setIsCreating(false);
      resetForm();
    } catch (err) {
      console.error("Failed to create persona:", err);
    }
  };

  const handleUpdate = async (id: string) => {
    try {
      await update(id, formData);
      setEditingId(null);
      resetForm();
    } catch (err) {
      console.error("Failed to update persona:", err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this persona?")) return;
    try {
      await deletePersona(id);
    } catch (err) {
      console.error("Failed to delete persona:", err);
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      tone_attributes: {
        formal: 0.3,
        conversational: 0.8,
        humorous: 0.4,
      },
      writing_samples: [],
      forbidden_phrases: [],
      preferred_phrases: [],
      expertise_areas: [],
    });
  };

  const startEdit = (persona: PersonaProfile) => {
    setEditingId(persona.id);
    setFormData({
      name: persona.name,
      description: persona.description || "",
      tone_attributes: persona.tone_attributes,
      writing_samples: persona.writing_samples,
      forbidden_phrases: persona.forbidden_phrases,
      preferred_phrases: persona.preferred_phrases,
      expertise_areas: persona.expertise_areas,
    });
  };

  if (loading && personas.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Persona Management</h1>
        <Button onClick={() => setIsCreating(true)} disabled={isCreating}>
          Create Persona
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {(isCreating || editingId) && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>{editingId ? "Edit Persona" : "Create New Persona"}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Name</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Professional Tech Writer"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Description</label>
              <Textarea
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Describe this persona's voice and style..."
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Formal</label>
                <Input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.tone_attributes?.formal || 0.3}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      tone_attributes: {
                        ...formData.tone_attributes!,
                        formal: parseFloat(e.target.value),
                      },
                    })
                  }
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Conversational</label>
                <Input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.tone_attributes?.conversational || 0.8}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      tone_attributes: {
                        ...formData.tone_attributes!,
                        conversational: parseFloat(e.target.value),
                      },
                    })
                  }
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Humorous</label>
                <Input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.tone_attributes?.humorous || 0.4}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      tone_attributes: {
                        ...formData.tone_attributes!,
                        humorous: parseFloat(e.target.value),
                      },
                    })
                  }
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Expertise Areas (comma-separated)</label>
              <Input
                value={formData.expertise_areas?.join(", ") || ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    expertise_areas: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                  })
                }
                placeholder="AI, Software Engineering, Cloud Computing"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Forbidden Phrases (comma-separated)</label>
              <Input
                value={formData.forbidden_phrases?.join(", ") || ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    forbidden_phrases: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                  })
                }
                placeholder="In today's world, Let's dive in"
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => {
                  if (editingId) {
                    handleUpdate(editingId);
                  } else {
                    handleCreate();
                  }
                }}
              >
                {editingId ? "Update" : "Create"}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setIsCreating(false);
                  setEditingId(null);
                  resetForm();
                }}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4">
        {personas.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No personas yet. Create your first persona to get started.
            </CardContent>
          </Card>
        ) : (
          personas.map((persona) => (
            <Card key={persona.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-xl">{persona.name}</CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      {persona.description || "No description"}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => startEdit(persona)}>
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(persona.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Formal:</span>{" "}
                    {persona.tone_attributes.formal}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Conversational:</span>{" "}
                    {persona.tone_attributes.conversational}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Humorous:</span>{" "}
                    {persona.tone_attributes.humorous}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Version:</span>{" "}
                    {persona.version}
                  </div>
                </div>
                {persona.expertise_areas.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {persona.expertise_areas.map((area) => (
                      <Badge key={area} variant="secondary">
                        {area}
                      </Badge>
                    ))}
                  </div>
                )}
                {persona.forbidden_phrases.length > 0 && (
                  <div className="mt-3">
                    <span className="text-sm text-muted-foreground">Forbidden:</span>{" "}
                    <span className="text-sm text-destructive">
                      {persona.forbidden_phrases.join(", ")}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
