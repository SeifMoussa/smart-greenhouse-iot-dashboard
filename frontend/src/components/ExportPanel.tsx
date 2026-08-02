import { useState } from "react";
import { ApiError, downloadExportCsv } from "../api/client";
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
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  function buildParams(): { from?: string; to?: string; type?: string } {
    const params: { from?: string; to?: string; type?: string } = {};
    if (range !== "all") {
      params.from = new Date(Date.now() - RANGE_MS[range]).toISOString();
      params.to = new Date().toISOString();
    }
    if (sensor) params.type = sensor;
    return params;
  }

  async function onDownload() {
    setError(undefined);
    setDownloading(true);
    try {
      await downloadExportCsv(buildParams());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Download failed.");
    } finally {
      setDownloading(false);
    }
  }

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
          <Button
            variant="secondary"
            type="button"
            data-testid="export-button"
            loading={downloading}
            onClick={onDownload}
            className="w-full"
          >
            Download
          </Button>
        </div>
      </div>
      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
        Maximum range is 30 days per export. The download streams from the backend.
      </p>
      {error && (
        <p role="alert" className="mt-2 text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </Card>
  );
}
