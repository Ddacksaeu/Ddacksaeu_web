import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { INITIAL_EVENTS, USER_PROFILE, type CalendarEvent, type UserProfile } from "./mock-data";
import {
  deleteEvent,
  getEvents,
  getFavorites,
  getProfile,
  saveEvent,
  saveFavorite,
  saveProfile,
} from "./api/me";

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
  const [favorites, setFavorites] = useState<string[]>([]);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>(INITIAL_EVENTS);
  const [cv, setCV] = useState<CVAnalysis | null>(null);
  const [profile, setProfile] = useState<UserProfile>(USER_PROFILE);

  useEffect(() => {
    void Promise.all([getProfile(), getFavorites(), getEvents()])
      .then(([nextProfile, nextFavorites, nextEvents]) => {
        setProfile(nextProfile);
        setFavorites(nextFavorites.labIds);
        setEvents(nextEvents.items);
      })
      .catch(() => undefined);
  }, []);

  const value = useMemo<AppState>(
    () => ({
      favorites,
      toggleFavorite: (id) =>
        setFavorites((current) => {
          const saved = !current.includes(id);
          void saveFavorite(id, saved).catch(() => setFavorites(current));
          return saved ? [...current, id] : current.filter((item) => item !== id);
        }),
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
      addEvent: (event) => {
        const temporary = { ...event, id: `pending-${Math.random().toString(36).slice(2, 8)}` };
        setEvents((current) => [...current, temporary]);
        void saveEvent(event)
          .then((saved) =>
            setEvents((current) =>
              current.map((item) => (item.id === temporary.id ? saved : item)),
            ),
          )
          .catch(() => setEvents((current) => current.filter((item) => item.id !== temporary.id)));
      },
      removeEvent: (id) =>
        setEvents((current) => {
          const removed = current.find((item) => item.id === id);
          void deleteEvent(id).catch(() => removed && setEvents((next) => [...next, removed]));
          return current.filter((item) => item.id !== id);
        }),
      cv,
      setCV,
      profile,
      updateProfile: (patch) =>
        setProfile((current) => {
          const next = { ...current, ...patch };
          void saveProfile(patch)
            .then((saved) => setProfile(saved))
            .catch(() => setProfile(current));
          return next;
        }),
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
