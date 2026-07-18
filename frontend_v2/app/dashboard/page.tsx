import { AppHeader } from "../../src/components/app-header";
import { DashboardHome } from "../../src/features/dashboard/dashboard-home";

export default function DashboardPage() {
  return (
    <div className="site-shell">
      <AppHeader current="dashboard" />
      <DashboardHome />
    </div>
  );
}
