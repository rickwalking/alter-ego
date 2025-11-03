import axios, { AxiosError } from 'axios';
import type { ChatRequest, ChatResponse } from '@/types';

/**
 * Base URL for API requests
 * Uses environment variable with fallback to localhost:8000
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Axios instance configured for chat API
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Custom error type for API errors
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public originalError?: AxiosError
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Send a chat message to the backend
 *
 * @param message - The user's message
 * @returns Promise with the AI response and timestamp
 * @throws ApiError if the request fails
 */
export async function sendMessage(message: string): Promise<ChatResponse> {
  try {
    const request: ChatRequest = { message };

    const response = await apiClient.post<ChatResponse>('/api/chat', request);

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.response) {
        // Server responded with error
        throw new ApiError(
          error.response.data?.message || 'Server error occurred',
          error.response.status,
          error
        );
      } else if (error.request) {
        // Request made but no response
        throw new ApiError(
          'Unable to connect to server. Please check if the backend is running.',
          undefined,
          error
        );
      }
    }

    // Unknown error
    throw new ApiError('An unexpected error occurred', undefined);
  }
}
