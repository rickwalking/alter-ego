/**
 * Custom hook for managing quality rubrics
 */

import { useState, useEffect } from "react";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type {
  QualityRubric,
  QualityRubricCreatePayload,
  QualityRubricUpdatePayload,
} from "../types";

const API_BASE = "/api";

export function useRubrics() {
  const [rubrics, setRubrics] = useState<QualityRubric[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRubrics = async () => {
    try {
      setLoading(true);
      const response = await authenticatedFetch(`${API_BASE}/rubrics`);
      if (!response.ok) {
        throw new Error("Failed to fetch rubrics");
      }
      const data = await response.json();
      setRubrics(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const createRubric = async (data: QualityRubricCreatePayload) => {
    const response = await authenticatedFetch(`${API_BASE}/rubrics`, {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error("Failed to create rubric");
    }
    const rubric = await response.json();
    setRubrics((prev) => [rubric, ...prev]);
    return rubric;
  };

  const updateRubric = async (id: string, data: QualityRubricUpdatePayload) => {
    const response = await authenticatedFetch(`${API_BASE}/rubrics/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error("Failed to update rubric");
    }
    const rubric = await response.json();
    setRubrics((prev) => prev.map((r) => (r.id === id ? rubric : r)));
    return rubric;
  };

  const deleteRubric = async (id: string) => {
    const response = await authenticatedFetch(`${API_BASE}/rubrics/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Failed to delete rubric");
    }
    setRubrics((prev) => prev.filter((r) => r.id !== id));
    return true;
  };

  useEffect(() => {
    void fetchRubrics();
  }, []);

  return {
    rubrics,
    loading,
    error,
    refetch: fetchRubrics,
    create: createRubric,
    update: updateRubric,
    delete: deleteRubric,
  };
}
