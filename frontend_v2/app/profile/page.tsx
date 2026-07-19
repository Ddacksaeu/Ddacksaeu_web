import { AppHeader } from "../../src/components/app-header";
import { RealProfileWorkspace } from "../../src/features/profile/real-profile-workspace";

export default function ProfilePage() {
  return (
    <main className="site-shell">
      <AppHeader current="profile" />
      <RealProfileWorkspace />
    </main>
  );
}
