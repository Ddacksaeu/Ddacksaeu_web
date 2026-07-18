import { randomUUID } from "node:crypto";

import type { ProfileRepository } from "../../server/db/profile-repository";
import type { OwnerId } from "../../server/session/owner-session";
import type { CvAsset, Profile, TargetLab } from "./domain";
import { MAX_CV_BYTES, validateCvUpload, type CvUpload } from "./cv-validation";

export type SaveProfileInput = {
  readonly consentToStorage: boolean;
  readonly displayName: string;
  readonly researchInterests: readonly string[];
  readonly preferredUniversity?: string;
  readonly applicationTerm?: string;
  readonly degreeProgram?: string;
};

export class ConsentRequiredError extends Error {
  readonly name = "ConsentRequiredError";

  constructor() {
    super("Storage consent is required");
  }
}

const MAX_CV_ASSETS = 3;
const MAX_TOTAL_CV_BYTES = MAX_CV_ASSETS * MAX_CV_BYTES;

export class ProfileQuotaError extends Error {
  readonly name = "ProfileQuotaError";

  constructor() {
    super("CV storage quota exceeded");
  }
}

export class ProfileService {
  constructor(private readonly repository: ProfileRepository) {}

  async saveProfile(
    ownerId: OwnerId,
    input: SaveProfileInput,
  ): Promise<Profile> {
    if (!input.consentToStorage) {
      throw new ConsentRequiredError();
    }
    const profile: Profile = {
      ownerId,
      displayName: input.displayName.trim(),
      researchInterests: input.researchInterests.flatMap((value) => {
        const normalized = value.trim();
        return normalized.length > 0 ? [normalized] : [];
      }),
      preferredUniversity: input.preferredUniversity?.trim() ?? "",
      applicationTerm: input.applicationTerm?.trim() ?? "",
      degreeProgram: input.degreeProgram?.trim() ?? "",
      consentedAt: new Date().toISOString(),
    };
    await this.repository.saveProfile(ownerId, profile);
    return profile;
  }

  async getProfile(ownerId: OwnerId): Promise<Profile | null> {
    return (await this.repository.read(ownerId)).profile;
  }

  async attachCv(ownerId: OwnerId, upload: CvUpload): Promise<CvAsset> {
    const records = await this.repository.read(ownerId);
    if (records.profile === null) {
      throw new ConsentRequiredError();
    }
    const valid = validateCvUpload(upload);
    const storedBytes = records.cvAssets.reduce((total, asset) => total + asset.byteLength, 0);
    if (records.cvAssets.length >= MAX_CV_ASSETS || storedBytes + valid.bytes.byteLength > MAX_TOTAL_CV_BYTES) {
      throw new ProfileQuotaError();
    }
    const asset: CvAsset = {
      id: randomUUID(),
      ownerId,
      fileName: valid.fileName,
      contentType: valid.contentType,
      byteLength: valid.bytes.byteLength,
      bytes: valid.bytes,
    };
    await this.repository.saveCvAsset(ownerId, asset);
    return asset;
  }

  async setTargetLab(ownerId: OwnerId, labId: string, saved: boolean): Promise<TargetLab> {
    const records = await this.repository.read(ownerId);
    if (records.profile === null) {
      throw new ConsentRequiredError();
    }
    const existing = records.targetLabs.find((target) => target.labId === labId);
    const target: TargetLab = existing ?? {
      id: randomUUID(),
      ownerId,
      labId,
      createdAt: new Date().toISOString(),
    };
    await this.repository.setTargetLab(ownerId, target, saved);
    return target;
  }

  async reset(ownerId: OwnerId): Promise<void> {
    await this.repository.reset(ownerId);
  }
}
