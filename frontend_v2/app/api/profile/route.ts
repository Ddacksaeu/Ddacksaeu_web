import { randomBytes } from "node:crypto";
import { join } from "node:path";

import { NextResponse } from "next/server";
import { z } from "zod";

import {
  InvalidCvError,
  MAX_CV_BYTES,
  validateCvUploadMetadata,
} from "../../../src/features/profile/cv-validation";
import {
  InvalidProfileInputError,
  parseProfileInput,
} from "../../../src/features/profile/profile-input";
import {
  ConsentRequiredError,
  ProfileQuotaError,
  ProfileService,
} from "../../../src/features/profile/profile-service";
import { LAB_CATALOG_FIXTURES } from "../../../src/fixtures/catalog";
import { FileProfileRepository } from "../../../src/server/db/profile-repository";
import {
  createAnonymousOwner,
  issueOwnerCookie,
  serializeOwnerCookie,
  verifyOwnerCookie,
  type OwnerId,
} from "../../../src/server/session/owner-session";

const repository = new FileProfileRepository(
  process.env["PROFILE_DATA_FILE"] ??
    join(process.cwd(), ".data", "profile-records.json"),
);
const service = new ProfileService(repository);

const EPHEMERAL_OWNER_SESSION_SECRET = randomBytes(32).toString("hex");
const MAX_JSON_REQUEST_BYTES = 64 * 1024;
const MAX_MULTIPART_REQUEST_BYTES = MAX_CV_BYTES + 64 * 1024;
const targetLabInputSchema = z.strictObject({
  labId: z.string(),
  saved: z.boolean(),
}).readonly();

function oversizedResponse(request: Request, maximumBytes: number): NextResponse | null {
  const raw = request.headers.get("content-length");
  if (raw === null) return null;
  const length = Number(raw);
  if (Number.isSafeInteger(length) && length >= 0 && length <= maximumBytes) return null;
  return NextResponse.json({ error: "Request body too large" }, { status: 413 });
}

function ownerSecret(): string {
  const secret = process.env["OWNER_SESSION_SECRET"];
  if (secret !== undefined && secret.length >= 16) {
    return secret;
  }
  return EPHEMERAL_OWNER_SESSION_SECRET;
}

type OwnerContext = {
  readonly ownerId: OwnerId;
  readonly setCookie: string | null;
};

function ownerContext(request: Request): OwnerContext {
  const secret = ownerSecret();
  const raw = request.headers
    .get("cookie")
    ?.split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith("grad_owner="))
    ?.slice("grad_owner=".length);
  const verified = raw === undefined ? null : verifyOwnerCookie(raw, secret);
  if (verified !== null) {
    return { ownerId: verified, setCookie: null };
  }
  const ownerId = createAnonymousOwner();
  return {
    ownerId,
    setCookie: serializeOwnerCookie(
      issueOwnerCookie(ownerId, secret),
      process.env["NODE_ENV"] === "production",
    ),
  };
}

function respond(
  body: unknown,
  status: number,
  context: OwnerContext,
): NextResponse {
  const response = NextResponse.json(body, { status });
  if (context.setCookie !== null) {
    response.headers.set("Set-Cookie", context.setCookie);
  }
  return response;
}

export async function GET(request: Request): Promise<NextResponse> {
  const context = ownerContext(request);
  const records = await repository.read(context.ownerId);
  const profile =
    records.profile === null
      ? null
      : {
          displayName: records.profile.displayName,
          researchInterests: records.profile.researchInterests,
          preferredUniversity: records.profile.preferredUniversity,
          applicationTerm: records.profile.applicationTerm,
          degreeProgram: records.profile.degreeProgram,
          consentedAt: records.profile.consentedAt,
        };
  return respond(
    {
      profile,
      targetLabIds: records.targetLabs.map((target) => target.labId),
      summary: {
        savedProfessors: records.targetLabs.length,
        contactDrafts: records.contactDrafts.length,
        schedules: records.scheduleItems.length,
      },
      cvAssets: records.cvAssets.map((asset) => ({
        id: asset.id,
        fileName: asset.fileName,
        contentType: asset.contentType,
        byteLength: asset.byteLength,
      })),
    },
    200,
    context,
  );
}

export async function PUT(request: Request): Promise<NextResponse> {
  const oversized = oversizedResponse(request, MAX_JSON_REQUEST_BYTES);
  if (oversized !== null) return oversized;
  const context = ownerContext(request);
  try {
    const profile = await service.saveProfile(
      context.ownerId,
      parseProfileInput(await request.json()),
    );
    return respond(
      {
        profile: {
          displayName: profile.displayName,
          researchInterests: profile.researchInterests,
          preferredUniversity: profile.preferredUniversity,
          applicationTerm: profile.applicationTerm,
          degreeProgram: profile.degreeProgram,
          consentedAt: profile.consentedAt,
        },
      },
      200,
      context,
    );
  } catch (error) {
    if (
      error instanceof ConsentRequiredError ||
      error instanceof InvalidProfileInputError
    ) {
      return respond({ error: error.message }, 400, context);
    }
    throw error;
  }
}

export async function PATCH(request: Request): Promise<NextResponse> {
  const oversized = oversizedResponse(request, MAX_JSON_REQUEST_BYTES);
  if (oversized !== null) return oversized;
  const context = ownerContext(request);
  const parsed = targetLabInputSchema.safeParse(await request.json());
  if (!parsed.success || !LAB_CATALOG_FIXTURES.some((lab) => lab.id === parsed.data.labId)) {
    return respond({ error: "Unknown professor" }, 400, context);
  }
  try {
    await service.setTargetLab(context.ownerId, parsed.data.labId, parsed.data.saved);
    return respond({ labId: parsed.data.labId, saved: parsed.data.saved }, 200, context);
  } catch (error) {
    if (error instanceof ConsentRequiredError) {
      return respond({ error: error.message }, 400, context);
    }
    throw error;
  }
}

export async function POST(request: Request): Promise<NextResponse> {
  const oversized = oversizedResponse(request, MAX_MULTIPART_REQUEST_BYTES);
  if (oversized !== null) return oversized;
  const context = ownerContext(request);
  try {
    const form = await request.formData();
    const value = form.get("cv");
    if (!(value instanceof File)) {
      return respond({ error: "CV file is required" }, 400, context);
    }
    validateCvUploadMetadata({
      byteLength: value.size,
      contentType: value.type,
      fileName: value.name,
    });
    const asset = await service.attachCv(context.ownerId, {
      bytes: new Uint8Array(await value.arrayBuffer()),
      contentType: value.type,
      fileName: value.name,
    });
    return respond(
      {
        cvAsset: {
          id: asset.id,
          fileName: asset.fileName,
          contentType: asset.contentType,
          byteLength: asset.byteLength,
        },
      },
      201,
      context,
    );
  } catch (error) {
    if (
      error instanceof InvalidCvError ||
      error instanceof ConsentRequiredError ||
      error instanceof ProfileQuotaError
    ) {
      return respond({ error: error.message }, 400, context);
    }
    throw error;
  }
}

export async function DELETE(request: Request): Promise<NextResponse> {
  const context = ownerContext(request);
  await service.reset(context.ownerId);
  return respond({ reset: true }, 200, context);
}
