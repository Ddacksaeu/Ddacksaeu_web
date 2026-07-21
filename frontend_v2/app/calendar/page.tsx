import { Suspense } from "react";
import { AppHeader } from "../../src/components/app-header";
import { RealCalendar } from "../../src/features/calendar/real-calendar";

export default function CalendarPage() {
  return <div className="site-shell"><AppHeader current="calendar" /><Suspense fallback={<main className="calendar-layout"><p role="status">Loading calendar...</p></main>}><RealCalendar /></Suspense></div>;
}
