import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { INITIAL_EVENTS, USER_PROFILE, type CalendarEvent, type UserProfile } from "./mock-data";

export type CVAnalysis = {
  keywords: string[];
  skills: string[];
  methodologies: string[];
  projects: string[];
  completeness: number;
};

type AppState = {
  favorites: string[];
  toggleFavorite: (id: string) => void;
  isFavorite: (id: string) => boolean;

  compareIds: string[];
  toggleCompare: (id: string) => void;
  clearCompare: () => void;

  events: CalendarEvent[];
  addEvent: (e: Omit<CalendarEvent, "id">) => void;
  removeEvent: (id: string) => void;

  cv: CVAnalysis | null;
  setCV: (v: CVAnalysis | null) => void;

  profile: UserProfile;
  updateProfile: (patch: Partial<UserProfile>) => void;
};

const Ctx = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [favorites, setFavorites] = useState<string[]>(["vislab", "nlplab"]);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>(INITIAL_EVENTS);
  const [cv, setCV] = useState<CVAnalysis | null>(null);
  const [profile, setProfile] = useState<UserProfile>(USER_PROFILE);

  const value = useMemo<AppState>(
    () => ({
      favorites,
      toggleFavorite: (id) =>
        setFavorites((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id])),
      isFavorite: (id) => favorites.includes(id),
      compareIds,
      toggleCompare: (id) =>
        setCompareIds((s) => {
          if (s.includes(id)) return s.filter((x) => x !== id);
          if (s.length >= 3) return s;
          return [...s, id];
        }),
      clearCompare: () => setCompareIds([]),
      events,
      addEvent: (e) =>
        setEvents((s) => [...s, { ...e, id: `e${Math.random().toString(36).slice(2, 8)}` }]),
      removeEvent: (id) => setEvents((s) => s.filter((e) => e.id !== id)),
      cv,
      setCV,
      profile,
      updateProfile: (patch) => setProfile((s) => ({ ...s, ...patch })),
    }),
    [favorites, compareIds, events, cv, profile],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAppState must be used inside AppStateProvider");
  return v;
}
