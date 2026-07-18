import { createHmac, randomUUID, timingSafeEqual } from "node:crypto";

export type OwnerId = Readonly<{ value: string }>;

export class InvalidOwnerSessionError extends Error {
  readonly name = "InvalidOwnerSessionError";
}

export function createOwnerId(value: string): OwnerId {
  if (!/^[A-Za-z0-9_-]{3,128}$/u.test(value)) {
    throw new InvalidOwnerSessionError("Invalid anonymous owner id");
  }
  return { value };
}

function signature(payload: string, secret: string): string {
  return createHmac("sha256", secret).update(payload).digest("base64url");
}

export function issueOwnerCookie(ownerId: OwnerId, secret: string): string {
  if (secret.length < 16) {
    throw new InvalidOwnerSessionError("Owner secret is too short");
  }
  const payload = Buffer.from(ownerId.value, "utf8").toString("base64url");
  return `${payload}.${signature(payload, secret)}`;
}

export function verifyOwnerCookie(
  cookie: string,
  secret: string,
): OwnerId | null {
  const separator = cookie.indexOf(".");
  if (separator <= 0) {
    return null;
  }
  const payload = cookie.slice(0, separator);
  const provided = Buffer.from(cookie.slice(separator + 1));
  const expected = Buffer.from(signature(payload, secret));
  if (
    provided.byteLength !== expected.byteLength ||
    !timingSafeEqual(provided, expected)
  ) {
    return null;
  }
  const decoded = Buffer.from(payload, "base64url").toString("utf8");
  try {
    return createOwnerId(decoded);
  } catch (error) {
    if (error instanceof InvalidOwnerSessionError) {
      return null;
    }
    throw error;
  }
}

export function createAnonymousOwner(): OwnerId {
  return createOwnerId(randomUUID());
}

export function serializeOwnerCookie(
  value: string,
  secure = false,
): string {
  const secureAttribute = secure ? "; Secure" : "";
  return `grad_owner=${value}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800${secureAttribute}`;
}
