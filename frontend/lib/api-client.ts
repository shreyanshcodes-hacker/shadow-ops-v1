/**
 * ShadowOps API Client Foundation
 * Centralized typed fetch wrapper handling auth headers, base URL, and standardized error envelopes.
 */

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: unknown;
    request_id?: string;
  };
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

let tokenProvider: (() => Promise<string | null>) | null = null;
let staticToken: string | null = null;

export function registerTokenProvider(provider: () => Promise<string | null>) {
  tokenProvider = provider;
}

export function setApiAuthToken(token: string | null) {
  staticToken = token;
}

export async function getAuthHeader(): Promise<string | null> {
  if (tokenProvider) {
    try {
      const token = await tokenProvider();
      if (token) return `Bearer ${token}`;
    } catch (e) {
      console.warn("Failed to obtain fresh token from tokenProvider", e);
    }
  }
  if (staticToken) {
    return `Bearer ${staticToken}`;
  }
  return null;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  headers.set("Accept", "application/json");

  const authHeader = await getAuthHeader();
  if (authHeader && !headers.has("Authorization")) {
    headers.set("Authorization", authHeader);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData: ApiError;
    try {
      errorData = await response.json();
    } catch {
      errorData = {
        error: {
          code: "HTTP_ERROR",
          message: `Request failed with status ${response.status}: ${response.statusText}`,
        },
      };
    }
    throw errorData;
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// Typed API Client helpers
export const apiClient = {
  get: <T>(endpoint: string, options?: RequestInit) =>
    apiRequest<T>(endpoint, { ...options, method: "GET" }),
    
  post: <T>(endpoint: string, body?: unknown, options?: RequestInit) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),
    
  put: <T>(endpoint: string, body?: unknown, options?: RequestInit) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),
    
  delete: <T>(endpoint: string, options?: RequestInit) =>
    apiRequest<T>(endpoint, { ...options, method: "DELETE" }),
};

export async function downloadFile(endpoint: string, fallbackFileName?: string): Promise<void> {
  const url = `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const headers = new Headers();
  const authHeader = await getAuthHeader();
  if (authHeader) headers.set("Authorization", authHeader);

  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`Download failed with status ${response.status}: ${response.statusText}`);
  }

  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;

  const cd = response.headers.get("content-disposition");
  let resolvedName = fallbackFileName;
  if (cd && cd.includes("filename=")) {
    resolvedName = cd.split("filename=")[1].replace(/["']/g, "").trim();
  }
  a.download = resolvedName || "download";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(blobUrl);
}
