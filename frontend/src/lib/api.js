const configuredUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const localApiUrl = `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;

export const API_BASE_URL = configuredUrl || localApiUrl;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("platesignal_access_token");
  const isFormData = options.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(body.detail || "Something went wrong. Please try again.", response.status);
  return body;
}

export function saveSession(session) {
  localStorage.setItem("platesignal_access_token", session.access_token);
  localStorage.setItem("platesignal_user", JSON.stringify(session.user));
}
