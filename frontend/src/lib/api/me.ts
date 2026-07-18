const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace(
  /\/$/,
  "",
);

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) throw new Error("Your changes could not be saved.");
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export type ServerProfile = {
  name: string;
  affiliation: string;
  status: string;
  program: string;
  interests: string[];
  skills: string[];
  methodologies: string[];
  projects: string[];
};
export type ServerEvent = {
  id: string;
  title: string;
  kind: "apply" | "contact" | "docs" | "interview";
  date: string;
  labId?: string;
  memo?: string;
};

export const getProfile = () => request<ServerProfile>("/me/profile");
export const saveProfile = (patch: Partial<ServerProfile>) =>
  request<ServerProfile>("/me/profile", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
export const getFavorites = () => request<{ labIds: string[] }>("/me/favorites");
export const saveFavorite = (labId: string, saved: boolean) =>
  request<void>(`/me/favorites/${encodeURIComponent(labId)}`, { method: saved ? "PUT" : "DELETE" });
export const getEvents = () => request<{ items: ServerEvent[] }>("/me/calendar-events");
export const saveEvent = (event: Omit<ServerEvent, "id">) =>
  request<ServerEvent>("/me/calendar-events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event),
  });
export const deleteEvent = (id: string) =>
  request<void>(`/me/calendar-events/${encodeURIComponent(id)}`, { method: "DELETE" });
