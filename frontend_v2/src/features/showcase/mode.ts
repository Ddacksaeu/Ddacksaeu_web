export const SHOWCASE_UNAVAILABLE_MESSAGE = "This public deployment showcases the frontend experience. The complete end-to-end workflow runs with the local FastAPI backend and is demonstrated in the submitted video.";

export function isShowcaseMode(): boolean {
  return process.env["NEXT_PUBLIC_DEPLOYMENT_MODE"] === "showcase";
}
