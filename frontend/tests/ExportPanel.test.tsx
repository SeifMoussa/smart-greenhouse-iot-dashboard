import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setAuthToken } from "../src/api/client";
import { ExportPanel } from "../src/components/ExportPanel";
import { renderWithQueryClient } from "./helpers";

function csvResponse(): Response {
  return new Response("id,sensor_id,type,value,unit,timestamp\n", {
    status: 200,
    headers: {
      "content-type": "text/csv",
      "content-disposition": 'attachment; filename="greenhouse-readings-test.csv"',
    },
  });
}

describe("<ExportPanel />", () => {
  beforeEach(() => {
    setAuthToken("test-token");
    URL.createObjectURL = vi.fn(() => "blob:mock-url");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setAuthToken(null);
  });

  it("sends the Bearer token and default range params on download", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => csvResponse());
    vi.stubGlobal("fetch", fetchMock);

    renderWithQueryClient(<ExportPanel />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("export-button"));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/api/export.csv?");
    expect(String(url)).toContain("from=");
    expect(String(url)).toContain("to=");
    expect((init as RequestInit).headers).toMatchObject({ Authorization: "Bearer test-token" });
  });

  it("omits time params when 'all' is selected", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => csvResponse());
    vi.stubGlobal("fetch", fetchMock);

    renderWithQueryClient(<ExportPanel />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(/export range/i), "all");
    await user.click(screen.getByTestId("export-button"));

    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).not.toContain("from=");
    expect(String(url)).not.toContain("to=");
  });

  it("includes type param when a sensor filter is selected", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => csvResponse());
    vi.stubGlobal("fetch", fetchMock);

    renderWithQueryClient(<ExportPanel />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(/sensor filter/i), "humidity");
    await user.click(screen.getByTestId("export-button"));

    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("type=humidity");
  });

  it("shows an error message when the download is rejected", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(null, { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);

    renderWithQueryClient(<ExportPanel />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("export-button"));

    expect(await screen.findByRole("alert")).toHaveTextContent(/export failed/i);
  });
});
