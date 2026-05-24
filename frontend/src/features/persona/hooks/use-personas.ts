/**
 * Custom hook for managing persona profiles
 */

import { useState, useEffect } from 'react';
import type { PersonaProfile, PersonaCreatePayload, PersonaUpdatePayload } from '../types';

const API_BASE = '/api';

export function usePersonas() {
  const [personas, setPersonas] = useState<PersonaProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPersonas = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/personas`);
      if (!response.ok) {
        throw new Error('Failed to fetch personas');
      }
      const data = await response.json();
      setPersonas(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const createPersona = async (data: PersonaCreatePayload) => {
    try {
      const response = await fetch(`${API_BASE}/personas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw new Error('Failed to create persona');
      }
      const persona = await response.json();
      setPersonas(prev => [persona, ...prev]);
      return persona;
    } catch (err) {
      throw err;
    }
  };

  const updatePersona = async (id: string, data: PersonaUpdatePayload) => {
    try {
      const response = await fetch(`${API_BASE}/personas/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw new Error('Failed to update persona');
      }
      const persona = await response.json();
      setPersonas(prev => prev.map(p => p.id === id ? persona : p));
      return persona;
    } catch (err) {
      throw err;
    }
  };

  const deletePersona = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/personas/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error('Failed to delete persona');
      }
      setPersonas(prev => prev.filter(p => p.id !== id));
      return true;
    } catch (err) {
      throw err;
    }
  };

  useEffect(() => {
    fetchPersonas();
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
