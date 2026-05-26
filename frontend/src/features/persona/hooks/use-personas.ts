/**
 * Custom hook for managing persona profiles
 */

import { useState, useEffect } from "react";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type {
  PersonaProfile,
  PersonaCreatePayload,
  PersonaUpdatePayload,
} from "../types";

const API_BASE = "/api";

export function usePersonas() {
  const [personas, setPersonas] = useState<PersonaProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPersonas = async () => {
    try {
      setLoading(true);
      const response = await authenticatedFetch(`${API_BASE}/personas`);
      if (!response.ok) {
        throw new Error("Failed to fetch personas");
      }
      const data = await response.json();
      setPersonas(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const createPersona = async (data: PersonaCreatePayload) => {
    const response = await authenticatedFetch(`${API_BASE}/personas`, {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error("Failed to create persona");
    }
    const persona = await response.json();
    setPersonas((prev) => [persona, ...prev]);
    return persona;
  };

  const updatePersona = async (id: string, data: PersonaUpdatePayload) => {
    const response = await authenticatedFetch(`${API_BASE}/personas/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error("Failed to update persona");
    }
    const persona = await response.json();
    setPersonas((prev) => prev.map((p) => (p.id === id ? persona : p)));
    return persona;
  };

  const deletePersona = async (id: string) => {
    const response = await authenticatedFetch(`${API_BASE}/personas/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Failed to delete persona");
    }
    setPersonas((prev) => prev.filter((p) => p.id !== id));
    return true;
  };

  useEffect(() => {
    void fetchPersonas();
  }, []);

  return {
    personas,
    loading,
    error,
    refetch: fetchPersonas,
    create: createPersona,
    update: updatePersona,
    delete: deletePersona,
  };
}
