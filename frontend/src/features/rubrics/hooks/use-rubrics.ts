/**
 * Custom hook for managing quality rubrics
 */

import { useState, useEffect } from 'react';
import type { QualityRubric, QualityRubricCreatePayload, QualityRubricUpdatePayload } from '../types';

const API_BASE = '/api';

export function useRubrics() {
  const [rubrics, setRubrics] = useState<QualityRubric[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRubrics = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/rubrics`);
      if (!response.ok) {
        throw new Error('Failed to fetch rubrics');
      }
      const data = await response.json();
      setRubrics(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const createRubric = async (data: QualityRubricCreatePayload) => {
    try {
      const response = await fetch(`${API_BASE}/rubrics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw new Error('Failed to create rubric');
      }
      const rubric = await response.json();
      setRubrics(prev => [rubric, ...prev]);
      return rubric;
    } catch (err) {
      throw err;
    }
  };

  const updateRubric = async (id: string, data: QualityRubricUpdatePayload) => {
    try {
      const response = await fetch(`${API_BASE}/rubrics/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw new Error('Failed to update rubric');
      }
      const rubric = await response.json();
      setRubrics(prev => prev.map(r => r.id === id ? rubric : r));
      return rubric;
    } catch (err) {
      throw err;
    }
  };

  const deleteRubric = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/rubrics/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error('Failed to delete rubric');
      }
      setRubrics(prev => prev.filter(r => r.id !== id));
      return true;
    } catch (err) {
      throw err;
    }
  };

  useEffect(() => {
    fetchRubrics();
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
