import { z } from "zod";

import type { SaveProfileInput } from "./profile-service";

const profileInputSchema = z
  .strictObject({
    consentToStorage: z.literal(true),
    displayName: z.string().trim().min(1).max(100),
    researchInterests: z.array(z.string().trim().min(1).max(100)).max(20).readonly(),
    preferredUniversity: z.string().trim().max(100).optional().default(""),
    applicationTerm: z.string().trim().max(50).optional().default(""),
    degreeProgram: z.string().trim().max(50).optional().default(""),
  })
  .readonly();

export class InvalidProfileInputError extends Error {
  readonly name = "InvalidProfileInputError";
}

export function parseProfileInput(value: unknown): SaveProfileInput {
  const result = profileInputSchema.safeParse(value);
  if (!result.success) {
    if (
      typeof value === "object" &&
      value !== null &&
      "consentToStorage" in value &&
      value.consentToStorage !== true
    ) {
      return {
        consentToStorage: false,
        displayName: "",
        researchInterests: [],
      };
    }
    throw new InvalidProfileInputError("Invalid profile fields");
  }
  return result.data;
}
