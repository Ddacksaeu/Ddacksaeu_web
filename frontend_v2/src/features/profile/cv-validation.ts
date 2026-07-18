export const MAX_CV_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["application/pdf", "text/plain"] as const;
const PDF_SIGNATURE = [37, 80, 68, 70, 45] as const;

type AllowedCvType = (typeof ALLOWED_TYPES)[number];

export type CvUpload = {
  readonly bytes: Uint8Array;
  readonly contentType: string;
  readonly fileName: string;
};

export type CvUploadMetadata = {
  readonly byteLength: number;
  readonly contentType: string;
  readonly fileName: string;
};

export type ValidatedCvUpload = {
  readonly bytes: Uint8Array;
  readonly contentType: AllowedCvType;
  readonly fileName: string;
};

export class InvalidCvError extends Error {
  readonly name = "InvalidCvError";

  constructor(
    readonly reason: "type" | "size" | "name" | "empty" | "signature",
  ) {
    super(`Invalid CV upload: ${reason}`);
  }
}

function hasPdfSignature(bytes: Uint8Array): boolean {
  if (bytes.byteLength < PDF_SIGNATURE.length) return false;
  for (const [index, byte] of PDF_SIGNATURE.entries()) {
    if (bytes[index] !== byte) return false;
  }
  return true;
}

export function validateCvUpload(input: CvUpload): ValidatedCvUpload {
  validateCvUploadMetadata({
    byteLength: input.bytes.byteLength,
    contentType: input.contentType,
    fileName: input.fileName,
  });
  const allowedType = ALLOWED_TYPES.find(
    (contentType) => contentType === input.contentType,
  );
  if (allowedType === undefined) {
    throw new InvalidCvError("type");
  }
  if (
    allowedType === "application/pdf" &&
    !hasPdfSignature(input.bytes)
  ) {
    throw new InvalidCvError("signature");
  }
  return {
    bytes: input.bytes,
    contentType: allowedType,
    fileName: input.fileName,
  };
}

export function validateCvUploadMetadata(input: CvUploadMetadata): void {
  if (!ALLOWED_TYPES.some((contentType) => contentType === input.contentType)) {
    throw new InvalidCvError("type");
  }
  if (input.byteLength > MAX_CV_BYTES) {
    throw new InvalidCvError("size");
  }
  if (input.byteLength === 0) {
    throw new InvalidCvError("empty");
  }
  if (input.fileName.trim().length === 0) {
    throw new InvalidCvError("name");
  }
}
