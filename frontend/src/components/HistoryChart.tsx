import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/endpoints";
import { type Reading, type SensorType, SENSOR_LABELS, SENSOR_TYPES } from "../types/api";
import { Card } from "./ui/Card";

type Range = "1h" | "24h" | "7d";

const RANGE_LABELS: Record<Range, string> = {
  "1h": "Last hour",
  "24h": "Last 24 hours",
  "7d": "Last 7 days",
};

const RANGE_MS: Record<Range, number> = {
  "1h": 60 * 60 * 1_000,
  "24h": 24 * 60 * 60 * 1_000,
  "7d": 7 * 24 * 60 * 60 * 1_000,
};

const RANGE_LIMIT: Record<Range, number> = {
  "1h": 720,
  "24h": 2_880,
  "7d": 10_000,
};

const SERIES_COLOR: Record<SensorType, string> = {
  temperature: "#ef4444",
  humidity: "#3b82f6",
  soil_moisture: "#10b981",
  light: "#f59e0b",
};

function bucket(readings: Reading[]): Array<Record<string, number | string>> {
  // Group by ISO-minute timestamp so the chart can show multiple series in one row.
  const map = new Map<string, Record<string, number | string>>();
  for (const r of readings) {
    const key = r.timestamp.slice(0, 16); // YYYY-MM-DDTHH:MM
    const row = map.get(key) ?? { time: key };
    row[r.type] = r.value;
    map.set(key, row);
  }
  return Array.from(map.values()).sort((a, b) => String(a.time).localeCompare(String(b.time)));
}

export function HistoryChart() {
  const [range, setRange] = useState<Range>("24h");

  const fromIso = useMemo(() => new Date(Date.now() - RANGE_MS[range]).toISOString(), [range]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["readings", "history", range],
    queryFn: ({ signal }) => api.listReadings({ from: fromIso, limit: RANGE_LIMIT[range] }, signal),
    refetchOnWindowFocus: false,
    staleTime: 30_000,
  });

  const chartData = useMemo(() => bucket(data ?? []), [data]);

  return (
    <Card
      title="History"
      action={
        <div
          role="group"
          aria-label="Time range"
          className="inline-flex gap-1 rounded-lg bg-slate-100 p-1 text-xs dark:bg-slate-800"
        >
          {(Object.keys(RANGE_LABELS) as Range[]).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRange(r)}
              aria-pressed={range === r}
              className={`rounded-md px-2 py-1 transition-colors ${
                range === r
                  ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-slate-100"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      }
    >
      {isLoading && <div className="h-72 text-sm text-slate-500">Loading…</div>}
      {isError && (
        <div className="h-72 text-sm text-red-600 dark:text-red-400">Could not load history.</div>
      )}
      {!isLoading && !isError && (
        <div className="h-72" data-testid="history-chart">
          {chartData.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              No readings in this range yet.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ left: 0, right: 8, top: 8, bottom: 8 }}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  className="stroke-slate-200 dark:stroke-slate-700"
                />
                <XAxis dataKey="time" tick={{ fontSize: 11 }} minTickGap={32} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                {SENSOR_TYPES.map((type) => (
                  <Line
                    key={type}
                    type="monotone"
                    dataKey={type}
                    name={SENSOR_LABELS[type]}
                    stroke={SERIES_COLOR[type]}
                    dot={false}
                    isAnimationActive={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      )}
    </Card>
  );
}
