import { randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

import {
  EMPTY_OWNER_RECORDS,
  type ContactDraft,
  type CvAsset,
  type OwnerRecords,
  type Profile,
  type ScheduleItem,
  type TargetLab,
} from "../../features/profile/domain";
import type { OwnerId } from "../session/owner-session";
import {
  decodeProfileDatabase,
  encodeProfileDatabase,
} from "./file-profile-codec";

export class CrossOwnerWriteError extends Error {
  readonly name = "CrossOwnerWriteError";

  constructor(
    readonly expected: OwnerId,
    readonly received: OwnerId,
  ) {
    super(`Owner mismatch: expected ${expected.value}`);
  }
}

function assertOwner(expected: OwnerId, received: OwnerId): void {
  if (expected.value !== received.value) {
    throw new CrossOwnerWriteError(expected, received);
  }
}

type RecordsUpdate = (records: OwnerRecords) => OwnerRecords;
type DatabaseUpdate = (database: Map<string, OwnerRecords>) => void;

export interface ProfileRepository {
  read(ownerId: OwnerId): Promise<OwnerRecords>;
  saveProfile(ownerId: OwnerId, profile: Profile): Promise<void>;
  saveCvAsset(ownerId: OwnerId, asset: CvAsset): Promise<void>;
  setTargetLab(ownerId: OwnerId, item: TargetLab, saved: boolean): Promise<void>;
  saveContactDraft(ownerId: OwnerId, item: ContactDraft): Promise<void>;
  saveScheduleItem(ownerId: OwnerId, item: ScheduleItem): Promise<void>;
  listCvAssets(ownerId: OwnerId): Promise<readonly CvAsset[]>;
  reset(ownerId: OwnerId): Promise<void>;
}

export class InMemoryProfileRepository implements ProfileRepository {
  private readonly records = new Map<string, OwnerRecords>();

  async read(ownerId: OwnerId): Promise<OwnerRecords> {
    return this.records.get(ownerId.value) ?? EMPTY_OWNER_RECORDS;
  }

  private async update(
    ownerId: OwnerId,
    update: RecordsUpdate,
  ): Promise<void> {
    this.records.set(ownerId.value, update(await this.read(ownerId)));
  }

  async saveProfile(ownerId: OwnerId, profile: Profile): Promise<void> {
    assertOwner(ownerId, profile.ownerId);
    await this.update(ownerId, (current) => ({ ...current, profile }));
  }

  async saveCvAsset(ownerId: OwnerId, asset: CvAsset): Promise<void> {
    assertOwner(ownerId, asset.ownerId);
    await this.update(ownerId, (current) => ({
      ...current,
      cvAssets: [...current.cvAssets, asset],
    }));
  }

  async setTargetLab(ownerId: OwnerId, item: TargetLab, saved: boolean): Promise<void> {
    assertOwner(ownerId, item.ownerId);
    await this.update(ownerId, (current) => ({
      ...current,
      targetLabs: saved
        ? [...current.targetLabs.filter((target) => target.labId !== item.labId), item]
        : current.targetLabs.filter((target) => target.labId !== item.labId),
    }));
  }

  async saveContactDraft(
    ownerId: OwnerId,
    item: ContactDraft,
  ): Promise<void> {
    assertOwner(ownerId, item.ownerId);
    await this.update(ownerId, (current) => ({
      ...current,
      contactDrafts: [...current.contactDrafts, item],
    }));
  }

  async saveScheduleItem(
    ownerId: OwnerId,
    item: ScheduleItem,
  ): Promise<void> {
    assertOwner(ownerId, item.ownerId);
    await this.update(ownerId, (current) => ({
      ...current,
      scheduleItems: [...current.scheduleItems, item],
    }));
  }

  async listCvAssets(ownerId: OwnerId): Promise<readonly CvAsset[]> {
    return (await this.read(ownerId)).cvAssets;
  }

  async reset(ownerId: OwnerId): Promise<void> {
    this.records.delete(ownerId.value);
  }
}

function isMissingFile(error: unknown): boolean {
  return error instanceof Error && "code" in error && error.code === "ENOENT";
}

export class FileProfileRepository implements ProfileRepository {
  private gate: Promise<void> = Promise.resolve();

  constructor(private readonly filePath: string) {}

  private async load(): Promise<Map<string, OwnerRecords>> {
    try {
      return decodeProfileDatabase(await readFile(this.filePath, "utf8"));
    } catch (error) {
      if (isMissingFile(error)) {
        return new Map();
      }
      throw error;
    }
  }

  private async persist(
    database: ReadonlyMap<string, OwnerRecords>,
  ): Promise<void> {
    await mkdir(dirname(this.filePath), { recursive: true });
    const temporary = `${this.filePath}.${randomUUID()}.tmp`;
    await writeFile(temporary, encodeProfileDatabase(database), {
      encoding: "utf8",
      mode: 0o600,
    });
    await rename(temporary, this.filePath);
  }

  async read(ownerId: OwnerId): Promise<OwnerRecords> {
    await this.gate;
    return (await this.load()).get(ownerId.value) ?? EMPTY_OWNER_RECORDS;
  }

  private async transact(update: DatabaseUpdate): Promise<void> {
    const previous = this.gate;
    let release = (): void => undefined;
    this.gate = new Promise((resolve) => {
      release = resolve;
    });
    await previous;
    try {
      const database = await this.load();
      update(database);
      await this.persist(database);
    } finally {
      release();
    }
  }

  private async update(
    ownerId: OwnerId,
    update: RecordsUpdate,
  ): Promise<void> {
    await this.transact((database) => {
      const current = database.get(ownerId.value) ?? EMPTY_OWNER_RECORDS;
      database.set(ownerId.value, update(current));
    });
  }

  async saveProfile(ownerId: OwnerId, profile: Profile): Promise<void> {
    assertOwner(ownerId, profile.ownerId);
    await this.update(ownerId, (current) => ({ ...current, profile }));
  }

  async saveCvAsset(ownerId: OwnerId, asset: CvAsset): Promise<void> {
    assertOwner(ownerId, asset.ownerId);
    await this.update(ownerId, (current) => ({
      ...current,
      cvAssets: [...current.cvAssets, asset],
    }));
  }

  async setTargetLab(ownerId: OwnerId, item: TargetLab, saved: boolean): Promise<void> {
    assertOwner(ownerId, item.ownerId);
    await this.update(ownerId, (current) => ({
      ...current,
      targetLabs: saved
        ? [...current.targetLabs.filter((target) => target.labId !== item.labId), item]
        : current.targetLabs.filter((target) => target.labId !== item.labId),
    }));
  }

  async saveContactDraft(
    ownerId: OwnerId,
    item: ContactDraft,
  ): Promise<void> {
    assertOwner(ownerId, item.ownerId);
    await this.update(ownerId, (current) => ({
      ...current,
      contactDrafts: [...current.contactDrafts, item],
    }));
  }

  async saveScheduleItem(
    ownerId: OwnerId,
    item: ScheduleItem,
  ): Promise<void> {
    assertOwner(ownerId, item.ownerId);
    await this.update(ownerId, (current) => ({
      ...current,
      scheduleItems: [...current.scheduleItems, item],
    }));
  }

  async listCvAssets(ownerId: OwnerId): Promise<readonly CvAsset[]> {
    return (await this.read(ownerId)).cvAssets;
  }

  async reset(ownerId: OwnerId): Promise<void> {
    await this.transact((database) => {
      database.delete(ownerId.value);
    });
  }
}
