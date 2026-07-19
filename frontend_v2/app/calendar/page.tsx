import { AppHeader } from "../../src/components/app-header";
import { RealCalendar } from "../../src/features/calendar/real-calendar";

export default function CalendarPage() { return <div className="site-shell"><AppHeader current="calendar" /><RealCalendar /></div>; }
