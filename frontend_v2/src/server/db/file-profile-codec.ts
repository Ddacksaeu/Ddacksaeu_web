import { z } from "zod";

import type {
  ContactDraft,
  CvAsset,
  OwnerRecords,
  Profile,
  ScheduleItem,
  TargetLab,
} from "../../features/profile/domain";
import { createOwnerId } from "../session/owner-session";

const ownedSchema = z.object({ ownerId: z.string().min(3) });
const profileSchema = ownedSchema.extend({
  displayName: z.string(),
  researchInterests: z.array(z.string()).readonly(),
  preferredUniversity: z.string().default(""),
  applicationTerm: z.string().default(""),
  degreeProgram: z.string().default(""),
  consentedAt: z.string(),
});
const cvSchema = ownedSchema.extend({
  id: z.string(),
  fileName: z.string(),
  contentType: z.union([
    z.literal("application/pdf"),
    z.literal("text/plain"),
  ]),
  byteLength: z.number().int().nonnegative(),
  bytes: z.string(),
});
const targetLabSchema = ownedSchema.extend({
  id: z.string(),
  labId: z.string(),
  createdAt: z.string(),
});
const draftSchema = ownedSchema.extend({
  id: z.string(),
  labId: z.string(),
  subject: z.string(),
  body: z.string(),
  updatedAt: z.string(),
});
const scheduleSchema = ownedSchema.extend({
  id: z.string(),
  title: z.string(),
  startsAt: z.string(),
  labId: z.string().nullable(),
});
const recordsSchema = z.object({
  profile: profileSchema.nullable(),
  cvAssets: z.array(cvSchema),
  targetLabs: z.array(targetLabSchema),
  contactDrafts: z.array(draftSchema),
  scheduleItems: z.array(scheduleSchema),
});
const databaseSchema = z.record(z.string(), recordsSchema);

export type ProfileDatabase = ReadonlyMap<string, OwnerRecords>;

function decodeProfile(value: z.infer<typeof profileSchema>): Profile {
  return { ...value, ownerId: createOwnerId(value.ownerId) };
}

function decodeCv(value: z.infer<typeof cvSchema>): CvAsset {
  return {
    ...value,
    ownerId: createOwnerId(value.ownerId),
    bytes: new Uint8Array(Buffer.from(value.bytes, "base64")),
  };
}

function decodeTargetLab(value: z.infer<typeof targetLabSchema>): TargetLab {
  return { ...value, ownerId: createOwnerId(value.ownerId) };
}

function decodeDraft(value: z.infer<typeof draftSchema>): ContactDraft {
  return { ...value, ownerId: createOwnerId(value.ownerId) };
}

function decodeSchedule(
  value: z.infer<typeof scheduleSchema>,
): ScheduleItem {
  return { ...value, ownerId: createOwnerId(value.ownerId) };
}

export function decodeProfileDatabase(text: string): Map<string, OwnerRecords> {
  const raw: unknown = JSON.parse(text);
  const parsed = databaseSchema.parse(raw);
  const database = new Map<string, OwnerRecords>();
  for (const [ownerId, records] of Object.entries(parsed)) {
    database.set(ownerId, {
      profile:
        records.profile === null ? null : decodeProfile(records.profile),
      cvAssets: records.cvAssets.map(decodeCv),
      targetLabs: records.targetLabs.map(decodeTargetLab),
      contactDrafts: records.contactDrafts.map(decodeDraft),
      scheduleItems: records.scheduleItems.map(decodeSchedule),
    });
  }
  return database;
}

export function encodeProfileDatabase(database: ProfileDatabase): string {
  const entries = [...database.entries()].map(([ownerId, records]) => [
    ownerId,
    {
      profile:
        records.profile === null
          ? null
          : { ...records.profile, ownerId: records.profile.ownerId.value },
      cvAssets: records.cvAssets.map((asset) => ({
        ...asset,
        ownerId: asset.ownerId.value,
        bytes: Buffer.from(asset.bytes).toString("base64"),
      })),
      targetLabs: records.targetLabs.map((item) => ({
        ...item,
        ownerId: item.ownerId.value,
      })),
      contactDrafts: records.contactDrafts.map((item) => ({
        ...item,
        ownerId: item.ownerId.value,
      })),
      scheduleItems: records.scheduleItems.map((item) => ({
        ...item,
        ownerId: item.ownerId.value,
      })),
    },
  ]);
  return JSON.stringify(Object.fromEntries(entries));
}
