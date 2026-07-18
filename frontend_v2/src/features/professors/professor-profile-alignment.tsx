"use client";

import ky from "ky";
import Link from "next/link";
import { useEffect, useState } from "react";

import { profileWorkspaceSchema, type ProfileWorkspaceData } from "../profile/profile-client-contract";
import styles from "./professor-explorer.module.css";

type ProfessorProfileAlignmentProperties = Readonly<{
  topics: readonly string[];
  variant: "summary" | "evidence";
}>;

export function ProfessorProfileAlignment({ topics, variant }: ProfessorProfileAlignmentProperties) {
  const [workspace, setWorkspace] = useState<ProfileWorkspaceData | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    void ky.get("/api/profile").json().then((value) => {
      if (active) setWorkspace(profileWorkspaceSchema.parse(value));
    }).catch(() => {
      if (active) setFailed(true);
    }).finally(() => {
      if (active) setReady(true);
    });
    return () => { active = false; };
  }, []);

  const interests = workspace?.profile?.researchInterests ?? [];
  const normalizedInterests = new Set(interests.map((value) => value.toLocaleLowerCase("en-US")));
  const matches = topics.filter((topic) => normalizedInterests.has(topic.toLocaleLowerCase("en-US")));

  if (variant === "summary") {
    if (!ready) return <><strong>Checking your research profile</strong><p>Loading saved keywords and CV status.</p></>;
    if (failed) return <><strong>Profile match unavailable</strong><p>Open Profile to check your saved information.</p></>;
    if (workspace?.profile === null || workspace === null) return <><strong>Create a profile to compare</strong><p>Add research keywords and a CV for evidence-based matching.</p></>;
    return <><strong>{matches.length} exact keyword {matches.length === 1 ? "match" : "matches"}</strong><p>{matches.length > 0 ? `Shared topics: ${matches.join(" · ")}` : "No exact topic overlap yet. Review adjacent methods and projects."}</p></>;
  }

  if (!ready) {
    return <div className={styles["fitCallout"]}><strong>Checking your research profile</strong><p>Loading saved keywords.</p></div>;
  }
  if (failed) {
    return <div className={styles["fitCallout"]}><strong>Profile match unavailable</strong><p>We could not load your saved profile. Open Profile and try again.</p><Link href="/profile">Open Profile</Link></div>;
  }
  if (workspace?.profile === null || workspace === null) {
    return <div className={styles["fitCallout"]}><strong>No research profile yet</strong><p>Create a profile to compare your interests with this lab’s topics.</p><Link href="/profile">Create research profile</Link></div>;
  }
  return <div className={styles["fitCallout"]}><strong>Compared with your saved profile</strong><p>Your keywords: {interests.length > 0 ? interests.join(" · ") : "No keywords saved"}</p><p>Exact overlaps: {matches.length > 0 ? matches.join(" · ") : "None"}</p></div>;
}
