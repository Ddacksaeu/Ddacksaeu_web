import { describe, expect, it } from "vitest";

import { InMemoryProfileRepository } from "../../server/db/profile-repository";
import { createOwnerId } from "../../server/session/owner-session";
import { ConsentRequiredError, ProfileService } from "./profile-service";

const ownerA = createOwnerId("owner-a");
const ownerB = createOwnerId("owner-b");

describe("ProfileService", () => {
  it("persists only after consent", async () => {
    // Given
    const service = new ProfileService(new InMemoryProfileRepository());

    // When
    const saved = await service.saveProfile(ownerA, {
      consentToStorage: true,
      displayName: "Alex Kim",
      researchInterests: ["NLP"],
    });

    // Then
    expect(saved.displayName).toBe("Alex Kim");
  });

  it("rejects storage without consent", async () => {
    // Given
    const service = new ProfileService(new InMemoryProfileRepository());

    // When
    const saving = service.saveProfile(ownerA, {
      consentToStorage: false,
      displayName: "Alex Kim",
      researchInterests: [],
    });

    // Then
    await expect(saving).rejects.toBeInstanceOf(ConsentRequiredError);
  });

  it("isolates reads by owner identity", async () => {
    // Given
    const service = new ProfileService(new InMemoryProfileRepository());
    await service.saveProfile(ownerA, {
      consentToStorage: true,
      displayName: "Owner A",
      researchInterests: ["vision"],
    });

    // When
    const ownerBProfile = await service.getProfile(ownerB);

    // Then
    expect(ownerBProfile).toBeNull();
  });

  it("resets related owner data without deleting another owner", async () => {
    // Given
    const repository = new InMemoryProfileRepository();
    const service = new ProfileService(repository);
    await service.saveProfile(ownerA, {
      consentToStorage: true,
      displayName: "Owner A",
      researchInterests: ["vision"],
    });
    await service.attachCv(ownerA, {
      bytes: new Uint8Array([37, 80, 68, 70, 45]),
      contentType: "application/pdf",
      fileName: "cv.pdf",
    });
    await service.saveProfile(ownerB, {
      consentToStorage: true,
      displayName: "Owner B",
      researchInterests: ["systems"],
    });

    // When
    await service.reset(ownerA);

    // Then
    expect(await service.getProfile(ownerA)).toBeNull();
    expect(await repository.listCvAssets(ownerA)).toEqual([]);
    expect((await service.getProfile(ownerB))?.displayName).toBe("Owner B");
  });

  it("limits CV assets per owner", async () => {
    const service = new ProfileService(new InMemoryProfileRepository());
    await service.saveProfile(ownerA, { consentToStorage: true, displayName: "Owner", researchInterests: [] });
    const upload = { bytes: new Uint8Array([37, 80, 68, 70, 45]), contentType: "application/pdf", fileName: "cv.pdf" };
    await service.attachCv(ownerA, upload);
    await service.attachCv(ownerA, upload);
    await service.attachCv(ownerA, upload);

    await expect(service.attachCv(ownerA, upload)).rejects.toThrow("CV storage quota exceeded");
  });
});
