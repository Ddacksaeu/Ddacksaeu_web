import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import type {
  ContactDraft,
  CvAsset,
  Profile,
  ScheduleItem,
  TargetLab,
} from "../../features/profile/domain";
import { createOwnerId, type OwnerId } from "../session/owner-session";
import {
  CrossOwnerWriteError,
  FileProfileRepository,
  type ProfileRepository,
} from "./profile-repository";

const ownerA = createOwnerId("owner-a");
const ownerB = createOwnerId("owner-b");
const profile: Profile = {
  ownerId: ownerA,
  displayName: "A",
  researchInterests: ["NLP"],
  preferredUniversity: "KAIST",
  applicationTerm: "Spring 2027",
  degreeProgram: "Master's",
  consentedAt: "2026-07-16T00:00:00.000Z",
};
const cv: CvAsset = {
  id: "cv-1",
  ownerId: ownerA,
  fileName: "cv.pdf",
  contentType: "application/pdf",
  byteLength: 5,
  bytes: new Uint8Array([37, 80, 68, 70, 45]),
};
const lab: TargetLab = {
  id: "lab-1",
  ownerId: ownerA,
  labId: "official-lab",
  createdAt: "2026-07-16T00:00:00.000Z",
};
const draft: ContactDraft = {
  id: "draft-1",
  ownerId: ownerA,
  labId: "official-lab",
  subject: "Question",
  body: "Hello",
  updatedAt: "2026-07-16T00:00:00.000Z",
};
const schedule: ScheduleItem = {
  id: "schedule-1",
  ownerId: ownerA,
  title: "Deadline",
  startsAt: "2026-08-01T00:00:00.000Z",
  labId: "official-lab",
};
const directories: string[] = [];

async function repositoryPath(): Promise<string> {
  const directory = await mkdtemp(join(tmpdir(), "grad-profile-"));
  directories.push(directory);
  return join(directory, "owners.json");
}

afterEach(async () => {
  await Promise.all(
    directories
      .splice(0)
      .map((directory) => rm(directory, { recursive: true, force: true })),
  );
});

describe("FileProfileRepository", () => {
  it("persists the complete owner aggregate across fresh instances", async () => {
    // Given
    const path = await repositoryPath();
    const first = new FileProfileRepository(path);
    await first.saveProfile(ownerA, profile);
    await first.saveCvAsset(ownerA, cv);
    await first.setTargetLab(ownerA, lab, true);
    await first.saveContactDraft(ownerA, draft);
    await first.saveScheduleItem(ownerA, schedule);
    // When
    const records = await new FileProfileRepository(path).read(ownerA);
    // Then
    expect(records).toEqual({
      profile,
      cvAssets: [cv],
      targetLabs: [lab],
      contactDrafts: [draft],
      scheduleItems: [schedule],
    });
  });

  const crossOwnerCases = [
    {
      name: "profile",
      write: (repository: ProfileRepository, ownerId: OwnerId) =>
        repository.saveProfile(ownerId, { ...profile, ownerId: ownerB }),
    },
    {
      name: "CV",
      write: (repository: ProfileRepository, ownerId: OwnerId) =>
        repository.saveCvAsset(ownerId, { ...cv, ownerId: ownerB }),
    },
    {
      name: "target lab",
      write: (repository: ProfileRepository, ownerId: OwnerId) =>
        repository.setTargetLab(ownerId, { ...lab, ownerId: ownerB }, true),
    },
    {
      name: "contact draft",
      write: (repository: ProfileRepository, ownerId: OwnerId) =>
        repository.saveContactDraft(ownerId, { ...draft, ownerId: ownerB }),
    },
    {
      name: "schedule item",
      write: (repository: ProfileRepository, ownerId: OwnerId) =>
        repository.saveScheduleItem(ownerId, { ...schedule, ownerId: ownerB }),
    },
  ] as const;

  it.each(crossOwnerCases)(
    "rejects a cross-owner $name write",
    async ({ write }) => {
      // Given
      const repository = new FileProfileRepository(await repositoryPath());
      // When
      const writing = write(repository, ownerA);
      // Then
      await expect(writing).rejects.toBeInstanceOf(CrossOwnerWriteError);
    },
  );

  it("persists full aggregate reset across a fresh instance", async () => {
    // Given
    const path = await repositoryPath();
    const first = new FileProfileRepository(path);
    await first.saveProfile(ownerA, profile);
    await first.saveCvAsset(ownerA, cv);
    await first.setTargetLab(ownerA, lab, true);
    await first.saveContactDraft(ownerA, draft);
    await first.saveScheduleItem(ownerA, schedule);
    // When
    await new FileProfileRepository(path).reset(ownerA);
    // Then
    expect(await new FileProfileRepository(path).read(ownerA)).toEqual({
      profile: null,
      cvAssets: [],
      targetLabs: [],
      contactDrafts: [],
      scheduleItems: [],
    });
  });
});
