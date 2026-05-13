import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LiveReadings } from "../src/components/LiveReadings";
import { renderWithQueryClient } from "./helpers";

function mockReadings() {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify([
            {
              id: 1,
              sensor_id: "esp32-01",
              type: "temperature",
              value: 22.5,
              unit: "C",
              timestamp: new Date().toISOString(),
              created_at: new Date().toISOString(),
            },
            {
              id: 2,
              sensor_id: "esp32-01",
              type: "humidity",
              value: 55.0,
              unit: "%",
              timestamp: new Date().toISOString(),
              created_at: new Date().toISOString(),
            },
          ]),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    ),
  );
}

describe("<LiveReadings />", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a tile for every supported sensor type", async () => {
    mockReadings();
    renderWithQueryClient(<LiveReadings />);
    await waitFor(() => {
      expect(screen.getByTestId("reading-tile-temperature")).toBeInTheDocument();
    });
    expect(screen.getByTestId("reading-tile-humidity")).toBeInTheDocument();
    expect(screen.getByTestId("reading-tile-soil_moisture")).toBeInTheDocument();
    expect(screen.getByTestId("reading-tile-light")).toBeInTheDocument();
  });

  it("shows the latest value and unit for a known reading", async () => {
    mockReadings();
    renderWithQueryClient(<LiveReadings />);
    const tile = await screen.findByTestId("reading-tile-temperature");
    expect(tile).toHaveTextContent("22.5");
    expect(tile).toHaveTextContent("°C");
  });

  it("shows 'No data yet' for sensor types without readings", async () => {
    mockReadings();
    renderWithQueryClient(<LiveReadings />);
    const lightTile = await screen.findByTestId("reading-tile-light");
    expect(lightTile).toHaveTextContent(/no data yet/i);
  });

  it("shows an error message when the backend rejects", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "boom" }), {
            status: 500,
            headers: { "content-type": "application/json" },
          }),
      ),
    );
    renderWithQueryClient(<LiveReadings />);
    await waitFor(() => {
      expect(screen.getByText(/could not load latest readings/i)).toBeInTheDocument();
    });
  });
});
