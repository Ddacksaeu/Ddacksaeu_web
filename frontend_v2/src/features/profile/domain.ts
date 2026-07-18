import type { OwnerId } from "../../server/session/owner-session";

export type Profile = {
  readonly ownerId: OwnerId;
  readonly displayName: string;
  readonly researchInterests: readonly string[];
  readonly preferredUniversity: string;
  readonly applicationTerm: string;
  readonly degreeProgram: string;
  readonly consentedAt: string;
};

export type CvAsset = {
  readonly id: string;
  readonly ownerId: OwnerId;
  readonly fileName: string;
  readonly contentType: "application/pdf" | "text/plain";
  readonly byteLength: number;
  readonly bytes: Uint8Array;
};

export type TargetLab = {
  readonly id: string;
  readonly ownerId: OwnerId;
  readonly labId: string;
  readonly createdAt: string;
};

export type ContactDraft = {
  readonly id: string;
  readonly ownerId: OwnerId;
  readonly labId: string;
  readonly subject: string;
  readonly body: string;
  readonly updatedAt: string;
};

export type ScheduleItem = {
  readonly id: string;
  readonly ownerId: OwnerId;
  readonly title: string;
  readonly startsAt: string;
  readonly labId: string | null;
};

export type OwnerRecords = {
  readonly profile: Profile | null;
  readonly cvAssets: readonly CvAsset[];
  readonly targetLabs: readonly TargetLab[];
  readonly contactDrafts: readonly ContactDraft[];
  readonly scheduleItems: readonly ScheduleItem[];
};

export const EMPTY_OWNER_RECORDS: OwnerRecords = {
  profile: null,
  cvAssets: [],
  targetLabs: [],
  contactDrafts: [],
  scheduleItems: [],
};
