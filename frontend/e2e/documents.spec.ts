import { expect, test } from "@playwright/test";
import path from "node:path";

const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/";
const VRAGENLIJST = path.join(import.meta.dirname, "fixtures", "Vragenlijst.pdf");

test("documenten: brochure attached, an uploaded Vragenlijst yields a door-verkoper bevinding and risico, removal rebuilds", async ({
  page,
  request,
}) => {
  await request.post("/api/listings", { data: { url: LISTING_URL } });
  await page.goto("/");
  await page.getByRole("button", { name: "Buchterweg 15" }).click();

  const documenten = page.getByRole("region", { name: "Documenten" });
  await expect(documenten.getByRole("link", { name: "Brochure (funda)" })).toBeVisible();
  await expect(documenten.getByText(/gelezen · 2 pagina's · 1 bevinding/)).toBeVisible();

  await documenten.getByLabel("Document uploaden").setInputFiles(VRAGENLIJST);
  await expect(documenten.getByRole("link", { name: "Vragenlijst.pdf" })).toBeVisible();

  const verkoper = page.locator("details", { has: page.getByRole("heading", { name: "Verkoper-informatie" }) });
  await expect(verkoper.getByText("“Asbest in de dakplaten van de schuur.”")).toBeVisible();
  await expect(verkoper.getByLabel("Bevinding door verkoper: Vragenlijst.pdf, pagina 2")).toBeVisible();
  await expect(page.getByText("Asbest aanwezig volgens de verkoper")).toBeVisible();

  await documenten.getByLabel("Document uploaden").setInputFiles({
    name: "Lijst van zaken.docx",
    mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    buffer: Buffer.from("PK not a pdf"),
  });
  await expect(documenten.getByText("kon niet gelezen worden (geen PDF)")).toBeVisible();

  for (const name of ["Vragenlijst.pdf", "Lijst van zaken.docx"]) {
    await documenten.getByRole("button", { name: `${name} verwijderen` }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Verwijderen" }).click();
    await expect(documenten.getByRole("link", { name })).toHaveCount(0);
  }
  await expect(page.getByText("Asbest aanwezig volgens de verkoper")).toHaveCount(0);
  await expect(verkoper.getByText("“De gordijnen blijven achter.”")).toBeVisible();
});
