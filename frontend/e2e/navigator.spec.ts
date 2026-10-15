import { test, expect } from "@playwright/test";

test("browse and immediately ask the assistant with relevant sources and conversation memory", async ({
  page,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (e) => failures.push(e.message));
  await page.goto("/");
  await expect(page.locator(".scholar-card")).toHaveCount(4);
  await expect(page.getByText("My profile", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Confirmed rule matches")).toHaveCount(0);
  await page.screenshot({ path: "../var/dashboard.png", fullPage: true });
  await page.getByRole("button", { name: /Ask about scholarships/ }).click();
  await expect(
    page.getByText("Ask anything about the scholarships in the dataset."),
  ).toBeVisible();
  // Exercise the real UI and backend/session plumbing; model text is controlled to keep browser tests offline.
  const calls: Record<string, unknown>[] = [];
  await page.route("**/api/agent/query", async (route) => {
    calls.push(route.request().postDataJSON());
    const response = {
      answer: "Pragati provides INR 50,000 per year for educational expenses.",
      sources: [
        {
          scheme_id:
            "pragati_scholarship_scheme_for_girl_students_technical_degree",
          scheme_name:
            "Pragati Scholarship Scheme For Girl Students (Technical Degree)",
          source_name: null,
          source_url: null,
          retrieved_from: "pragati:benefits:0",
        },
      ],
      status: "success",
      error: null,
    };
    await route.fulfill({ json: response });
  });
  await page
    .getByLabel("Ask a scholarship question")
    .fill("Tell me about Pragati.");
  await page.getByRole("button", { name: /Send/ }).click();
  await expect(page.locator(".message.assistant")).toContainText("50,000");
  expect(calls[0]).not.toHaveProperty("profile");
  await page.getByText("Sources (1)").click();
  await expect(page.locator(".source strong")).toContainText(
    "Pragati Scholarship",
  );
  await page.route("**/api/sessions/*", async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    await route.fulfill({
      json: {
        context: {
          messages: [
            { role: "user", content: { question: "Tell me about Pragati." } },
            {
              role: "assistant",
              content: {
                answer:
                  "Pragati provides INR 50,000 per year for educational expenses.",
                status: "success",
                sources: [],
              },
            },
          ],
        },
      },
    });
  });
  await page.getByRole("link", { name: "View Full Scheme" }).click();
  await expect(page).toHaveURL(
    /#\/scholarships\/pragati_scholarship_scheme_for_girl_students_technical_degree$/,
  );
  await expect(
    page.getByRole("heading", { name: "Application procedure", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Exclusions", exact: true }),
  ).toBeVisible();
  await page.locator('nav a[href="#/assistant"]').click();
  await page
    .getByLabel("Ask a scholarship question")
    .fill("How much does it provide?");
  await page.getByRole("button", { name: /Send/ }).click();
  await expect(page.locator(".message.assistant")).toHaveCount(2);
  expect(calls[1].session_id).toEqual(calls[0].session_id);
  await page.locator('nav a[href="#/scholarships"]').click();
  await expect(page.locator(".scholar-card")).toHaveCount(16);
  await page
    .locator(".scholar-card")
    .filter({ hasText: "Pragati" })
    .first()
    .getByRole("link", { name: /View details/ })
    .click();
  await expect(
    page.getByRole("heading", { name: "Eligibility criteria" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Required documents", exact: true }),
  ).toBeVisible();
  expect(failures).toEqual([]);
});

test("assistant failure is visible", async ({ page }) => {
  await page.goto("/#/assistant");
  await page.route("**/api/agent/query", (route) =>
    route.fulfill({
      status: 503,
      json: {
        status: "error",
        error: {
          code: "LLM_RATE_LIMITED",
          message: "Provider quota reached. Please try again.",
        },
      },
    }),
  );
  await page.getByLabel("Ask a scholarship question").fill("Pragati?");
  await page.getByRole("button", { name: /Send/ }).click();
  await expect(page.getByRole("alert")).toContainText("Provider quota reached");
  await expect(page.locator(".message.assistant")).toHaveCount(0);
});

test("mobile overview fits the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".scholar-card")).toHaveCount(4);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "../var/mobile.png", fullPage: true });
});

test("off-domain requests skip model generation and return scholarship guidance", async ({
  page,
}) => {
  await page.goto("/#/assistant");
  await page.getByLabel("Ask a scholarship question").fill("What is 1+1?");
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/agent/query"),
  );
  await page.getByRole("button", { name: /Send/ }).click();
  const data = await (await response).json();
  expect(data.status).toBe("out_of_scope");
  expect(data.sources).toEqual([]);
  await expect(page.locator(".message.assistant")).toContainText(
    "I can help with the scholarship schemes",
  );
  await expect(page.locator(".message.assistant")).not.toContainText("1+1=2");
});

test("all 16 scheme identifiers resolve to complete internal detail pages", async ({
  page,
  request,
}) => {
  const response = await request.post("/api/scholarships/search", {
    data: { top_k: 16 },
  });
  const { results } = await response.json();
  expect(results).toHaveLength(16);
  await page.goto("/#/scholarships");
  for (const scheme of results) {
    await page.evaluate((id) => {
      window.location.hash = "/scholarships/" + encodeURIComponent(id);
    }, scheme.scheme_id);
    await expect(page.locator(".detail-heading h2")).toHaveText(scheme.name);
    await expect(
      page.getByRole("heading", { name: "Application procedure", exact: true }),
    ).toBeVisible();
  }
});
