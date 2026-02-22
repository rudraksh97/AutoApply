export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/api";

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null;

    // Do NOT override Content-Type when body is FormData — the browser sets it automatically
    // with the correct multipart boundary. Forcing application/json breaks file uploads.
    const isFormData = options.body instanceof FormData;

    const headers: Record<string, string> = {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(options.headers as Record<string, string> || {}),
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    };

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        if (typeof window !== "undefined") {
            localStorage.removeItem("token");
        }
    }

    return response;
}
