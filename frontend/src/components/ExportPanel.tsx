import { useState } from "react";
import { buildExportUrl } from "../api/client";
import { type SensorType, SENSOR_LABELS, SENSOR_TYPES } from "../types/api";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

type Range = "1h" | "24h" | "7d" | "all";

const RANGE_LABELS: Record<Range, string> = {
  "1h": "Last hour",
  "24h": "Last 24 hours",
  "7d": "Last 7 days",
  all: "All time",
};

const RANGE_MS: Record<Exclude<Range, "all">, number> = {
  "1h": 60 * 60 * 1_000,
  "24h": 24 * 60 * 60 * 1_000,
  "7d": 7 * 24 * 60 * 60 * 1_000,
};

export function ExportPanel() {
  const [range, setRange] = useState<Range>("24h");
  const [sensor, setSensor] = useState<SensorType | "">("");

  const url = (() => {
    const params: { from?: string; to?: string; type?: string } = {};
    if (range !== "all") {
      params.from = new Date(Date.now() - RANGE_MS[range]).toISOString();
      params.to = new Date().toISOString();
    }
    if (sensor) params.type = sensor;
    return buildExportUrl(params);
  })();

  return (
    <Card title="Export CSV">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto]">
        <label className="block text-xs text-slate-600 dark:text-slate-400">
          Range
          <select
            value={range}
            onChange={(e) => setRange(e.target.value as Range)}
            aria-label="Export range"
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            {(Object.keys(RANGE_LABELS) as Range[]).map((r) => (
              <option key={r} value={r}>
                {RANGE_LABELS[r]}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-slate-600 dark:text-slate-400">
          Sensor (optional)
          <select
            value={sensor}
            onChange={(e) => setSensor(e.target.value as SensorType | "")}
            aria-label="Sensor filter"
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="">All sensors</option>
            {SENSOR_TYPES.map((t) => (
              <option key={t} value={t}>
                {SENSOR_LABELS[t]}
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-end">
          <a
            href={url}
            data-testid="export-link"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex w-full items-center justify-center"
          >
            <Button variant="secondary" type="button" className="w-full">
              Download
            </Button>
          </a>
        </div>
      </div>
      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
        Maximum range is 30 days per export. The download streams from the backend.
      </p>
    </Card>
  );
}
