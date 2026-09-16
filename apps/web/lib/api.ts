export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000/v1`
    : "http://127.0.0.1:8000/v1");

export interface ApiError {
  code: string;
  message: string;
  details?: any;
}

export class ApiException extends Error {
  code: string;
  details?: any;
  status: number;

  constructor(status: number, error: ApiError) {
    super(error.message);
    this.name = "ApiException";
    this.code = error.code;
    this.details = error.details;
    this.status = status;
  }
}

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("hk_token");
  if (!token || token === "undefined" || token === "null" || token.trim() === "") {
    return null;
  }
  return token;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Only set Content-Type if not sending FormData
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const url = `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (netErr: any) {
    throw new ApiException(0, {
      code: "NETWORK_ERROR",
      message: netErr?.message
        ? `Cannot reach backend at ${url}: ${netErr.message}`
        : `Connection to backend server at ${url} failed. Ensure backend is running.`,
    });
  }

  if (!response.ok) {
    let errorData: any = {};
    try {
      errorData = await response.json();
    } catch {
      // ignore
    }

    let code = "UNKNOWN_ERROR";
    let message = response.statusText || `Request failed with status ${response.status}`;
    let details: any = undefined;

    if (errorData?.error?.message) {
      message = errorData.error.message;
      code = errorData.error.code || code;
      details = errorData.error.details;
    } else if (Array.isArray(errorData?.detail)) {
      code = "VALIDATION_ERROR";
      details = errorData.detail;
      const msgs = errorData.detail.map((d: any) => {
        const field = (d.loc || []).filter((x: any) => x !== "body").join(".");
        return field ? `${field}: ${d.msg}` : d.msg;
      });
      message = msgs.join("; ") || "Validation failed";
    } else if (typeof errorData?.detail === "string") {
      message = errorData.detail;
    }

    const err: ApiError = {
      code,
      message,
      details,
    };
    throw new ApiException(response.status, err);
  }

  return response.json() as Promise<T>;
}
