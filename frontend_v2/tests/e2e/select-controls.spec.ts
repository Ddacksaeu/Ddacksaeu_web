import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("single-select controls share one centered chevron and content inset", async ({ page }) => {
  await useSignedInDemo(page);

  for (const target of [
    { path: "/calendar", selector: "#calendar-institution" },
    { path: "/professors", selector: ".catalog-select-field select" },
    { path: "/cv", selector: "select" },
  ]) {
    await page.goto(target.path);
    const select = page.locator(target.selector).first();
    const styles = await select.evaluate((element) => {
      const computed = getComputedStyle(element);
      return {
        appearance: computed.appearance,
        backgroundImage: computed.backgroundImage,
        backgroundPosition: computed.backgroundPosition,
        paddingRight: computed.paddingRight,
        paddingBottom: computed.paddingBottom,
      };
    });

    expect(styles).toMatchObject({
      appearance: "none",
      backgroundPosition: "calc(100% - 8px) 50%",
      paddingRight: "36px",
      paddingBottom: "1px",
    });
    expect(styles.backgroundImage).toContain("data:image/svg+xml");
  }
});
