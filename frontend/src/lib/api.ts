import { useAuthStore, getAuthHeaders } from '../store/useAuthStore';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Core fetch wrapper. Injects Authorization header automatically, handles 401
 * by clearing auth state and redirecting to /login.
 */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const authHeaders = getAuthHeaders();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...authHeaders,
    ...(options.headers as Record<string, string> | undefined),
  };

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Token expired or invalid — force logout
    useAuthStore.getState().logout();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }

  return response;
}

/**
 * Typed GET helper. Returns parsed JSON or throws on non-ok responses.
 */
export async function apiGet<T = unknown>(path: string): Promise<T> {
  const response = await apiFetch(path, { method: 'GET' });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`GET ${path} failed (${response.status}): ${errorText}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Typed POST helper. Sends JSON body, returns parsed JSON or throws on non-ok responses.
 */
export async function apiPost<T = unknown>(path: string, body?: unknown): Promise<T> {
  const response = await apiFetch(path, {
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`POST ${path} failed (${response.status}): ${errorText}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Typed PUT helper. Sends JSON body, returns parsed JSON or throws on non-ok responses.
 */
export async function apiPut<T = unknown>(path: string, body?: unknown): Promise<T> {
  const response = await apiFetch(path, {
    method: 'PUT',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`PUT ${path} failed (${response.status}): ${errorText}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Typed DELETE helper.
 */
export async function apiDelete<T = unknown>(path: string): Promise<T> {
  const response = await apiFetch(path, { method: 'DELETE' });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`DELETE ${path} failed (${response.status}): ${errorText}`);
  }

  return response.json() as Promise<T>;
}
