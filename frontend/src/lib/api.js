// Cliente mínimo para la API del Amigo Secreto.
// Las cookies de sesión viajan solas con credentials: "include".

export const API_BASE =
  (typeof import.meta !== "undefined" && import.meta.env.PUBLIC_API_URL) || "";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

/** Petición genérica. Lanza ApiError si la respuesta no es 2xx. */
export async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (data.detail) detail = JSON.stringify(data.detail);
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(detail, res.status);
  }

  return res.status === 204 ? null : res.json();
}

/** ¿Hay sesión iniciada? Devuelve el participante o null. */
export async function quienSoy() {
  try {
    return await api("/api/auth/yo");
  } catch (e) {
    if (e.status === 401) return null;
    throw e;
  }
}
