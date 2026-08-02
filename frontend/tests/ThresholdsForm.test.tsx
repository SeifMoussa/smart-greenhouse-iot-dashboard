import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ThresholdsForm } from "../src/components/ThresholdsForm";
import { renderWithProviders } from "./helpers";

const defaultThresholds = [
  {
    type: "temperature",
    min_value: 15,
    max_value: 32,
    updated_at: "2026-01-01T00:00:00",
  },
  { type: "humidity", min_value: 40, max_value: 80, updated_at: "2026-01-01T00:00:00" },
  {
    type: "soil_moisture",
    min_value: 30,
    max_value: 80,
    updated_at: "2026-01-01T00:00:00",
  },
  { type: "light", min_value: 200, max_value: 1500, updated_at: "2026-01-01T00:00:00" },
];

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("<ThresholdsForm />", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads and displays current thresholds", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(defaultThresholds)),
    );
    renderWithProviders(<ThresholdsForm />);
    const tempForm = await screen.findByTestId("threshold-form-temperature");
    expect(within(tempForm).getByLabelText(/minimum/i)).toHaveValue(15);
    expect(within(tempForm).getByLabelText(/maximum/i)).toHaveValue(32);
  });

  it("rejects min >= max client-side without calling the API", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => jsonResponse(defaultThresholds));
    vi.stubGlobal("fetch", fetchMock);
    renderWithProviders(<ThresholdsForm />);
    const tempForm = await screen.findByTestId("threshold-form-temperature");

    const min = within(tempForm).getByLabelText(/minimum/i);
    const max = within(tempForm).getByLabelText(/maximum/i);
    const user = userEvent.setup();

    await user.clear(min);
    await user.type(min, "30");
    await user.clear(max);
    await user.type(max, "20");
    await user.click(within(tempForm).getByRole("button", { name: /save/i }));

    expect(
      within(tempForm).getByText(/minimum must be strictly less than maximum/i),
    ).toBeInTheDocument();
    // Only the initial GET happened — no PUT.
    const putCalls = fetchMock.mock.calls.filter(
      ([, init]) => (init as RequestInit | undefined)?.method === "PUT",
    );
    expect(putCalls).toHaveLength(0);
  });

  it("submits a valid update to the API", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (_url, init) => {
      if (init?.method === "PUT") {
        return jsonResponse({
          type: "temperature",
          min_value: 10,
          max_value: 30,
          updated_at: "2026-01-01T01:00:00",
        });
      }
      return jsonResponse(defaultThresholds);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithProviders(<ThresholdsForm />);
    const tempForm = await screen.findByTestId("threshold-form-temperature");

    const min = within(tempForm).getByLabelText(/minimum/i);
    const max = within(tempForm).getByLabelText(/maximum/i);
    const user = userEvent.setup();

    await user.clear(min);
    await user.type(min, "10");
    await user.clear(max);
    await user.type(max, "30");
    await user.click(within(tempForm).getByRole("button", { name: /save/i }));

    await waitFor(() => expect(within(tempForm).getByText(/saved/i)).toBeInTheDocument());

    const putCalls = fetchMock.mock.calls.filter(
      ([, init]) => (init as RequestInit | undefined)?.method === "PUT",
    );
    expect(putCalls).toHaveLength(1);
    const putCall = putCalls[0];
    expect(putCall).toBeDefined();
    const putUrl = putCall![0];
    const putInit = putCall![1] as RequestInit;
    expect(String(putUrl)).toContain("/api/thresholds/temperature");
    expect(JSON.parse(String(putInit.body))).toEqual({
      min_value: 10,
      max_value: 30,
    });
  });

  it("disables editing for the viewer role and never calls PUT", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => jsonResponse(defaultThresholds));
    vi.stubGlobal("fetch", fetchMock);

    renderWithProviders(<ThresholdsForm />, { role: "viewer" });
    const tempForm = await screen.findByTestId("threshold-form-temperature");

    expect(within(tempForm).getByLabelText(/minimum/i)).toBeDisabled();
    expect(within(tempForm).getByLabelText(/maximum/i)).toBeDisabled();
    expect(within(tempForm).getByRole("button", { name: /save/i })).toBeDisabled();
    expect(within(tempForm).getByText(/viewers can't change thresholds/i)).toBeInTheDocument();

    const putCalls = fetchMock.mock.calls.filter(
      ([, init]) => (init as RequestInit | undefined)?.method === "PUT",
    );
    expect(putCalls).toHaveLength(0);
  });
});
