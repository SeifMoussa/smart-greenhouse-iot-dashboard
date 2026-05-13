import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ExportPanel } from "../src/components/ExportPanel";
import { renderWithQueryClient } from "./helpers";

describe("<ExportPanel />", () => {
  it("renders a download link with the correct base path", () => {
    renderWithQueryClient(<ExportPanel />);
    const link = screen.getByTestId("export-link");
    expect(link.getAttribute("href")).toMatch(/\/api\/export\.csv\?.+/);
  });

  it("includes from and to params for ranged exports", () => {
    renderWithQueryClient(<ExportPanel />);
    const link = screen.getByTestId("export-link");
    const href = link.getAttribute("href")!;
    expect(href).toContain("from=");
    expect(href).toContain("to=");
  });

  it("omits time params when 'all' is selected", async () => {
    renderWithQueryClient(<ExportPanel />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(/export range/i), "all");
    const href = screen.getByTestId("export-link").getAttribute("href")!;
    expect(href).not.toContain("from=");
    expect(href).not.toContain("to=");
  });

  it("includes type param when a sensor filter is selected", async () => {
    renderWithQueryClient(<ExportPanel />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(/sensor filter/i), "humidity");
    const href = screen.getByTestId("export-link").getAttribute("href")!;
    expect(href).toContain("type=humidity");
  });
});
