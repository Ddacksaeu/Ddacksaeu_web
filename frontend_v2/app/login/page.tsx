"use client";

import { useRouter } from "next/navigation";
import { AppHeader } from "../../src/components/app-header";
import { startDemoSession } from "../../src/features/auth/demo-session";
import styles from "../../src/styles/auth.module.css";

export default function LoginPage() {
  const router = useRouter();
  return (
    <div className="site-shell">
      <AppHeader />
      <main className={styles["shell"]}>
        <form className={styles["card"]} action={() => { startDemoSession(window.localStorage); router.push("/onboarding"); }}>
          <p className={styles["eyebrow"]}>WELCOME TO Ddaksaeu</p>
          <h1>Graduate school planning,<br />all in one place</h1>
          <p className={styles["lead"]}>Manage professor discovery, CV analysis, outreach drafts, and application deadlines in one flow.</p>
          <label className={styles["field"]}>Username<input autoComplete="username" placeholder="Enter any username" required type="text" /></label>
          <label className={styles["field"]}>Password<input autoComplete="current-password" placeholder="Enter any password" required type="password" /></label>
          <button className={styles["primary"]} type="submit">Sign in</button>
          <p className={styles["legal"]}>Your credentials are not stored or <span className={styles["keep"]}>sent.</span></p>
        </form>
      </main>
    </div>
  );
}
