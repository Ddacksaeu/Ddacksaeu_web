import { AppHeader } from "../../src/components/app-header";
import { ProfileWorkspace } from "../../src/features/profile/profile-workspace";

export default function ProfilePage() {
  return (
    <main className="site-shell">
      <AppHeader current="profile" />
      <ProfileWorkspace />
    </main>
  );
}