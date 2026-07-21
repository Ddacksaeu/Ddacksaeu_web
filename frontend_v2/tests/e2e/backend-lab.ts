import { expect, type APIRequestContext } from "@playwright/test";
import { z } from "zod";

const labSearchSchema = z.object({
  items: z.array(z.object({
    id: z.string(),
    name: z.string(),
    professorName: z.string(),
  })),
});

export async function getFirstBackendLab(request: APIRequestContext) {
  const response = await request.get("http://127.0.0.1:8000/api/v1/labs?page=1&page_size=1");
  expect(response.ok()).toBe(true);
  const result = labSearchSchema.parse(await response.json());
  const lab = result.items.at(0);
  if (lab === undefined) {
    throw new RangeError("Frontend E2E tests require at least one backend lab.");
  }
  return lab;
}
