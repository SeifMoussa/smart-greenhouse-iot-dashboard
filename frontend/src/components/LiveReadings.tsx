import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { api } from "../api/endpoints";
import {
  type Reading,
  type SensorType,
  SENSOR_LABELS,
  SENSOR_TYPES,
  SENSOR_UNITS,
} from "../types/api";
import { Card } from "./ui/Card";

const SENSOR_ICONS: Record<SensorType, string> = {
  temperature: "🌡️",
  humidity: "💧",
  soil_moisture: "🌱",
  light: "💡",
};

function formatValue(value: number, type: SensorType): string {
  if (type === "light") return Math.round(value).toString();
  return value.toFixed(1);
}

function formatRelative(timestamp: string): string {
  const ms = Date.now() - new Date(timestamp).getTime();
  if (ms < 0) return "just now";
  const seconds = Math.floor(ms / 1000);
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(timestamp).toLocaleString();
}

function Trend({ direction }: { direction: "up" | "down" | "flat" }) {
  if (direction === "up") return <span aria-label="trending up">▲</span>;
  if (direction === "down") return <span aria-label="trending down">▼</span>;
  return <span aria-label="stable">—</span>;
}

function ReadingTile({ type, reading }: { type: SensorType; reading?: Reading }) {
  const previous = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (reading) previous.current = reading.value;
  }, [reading?.id, reading?.value]); // eslint-disable-line react-hooks/exhaustive-deps

  let direction: "up" | "down" | "flat" = "flat";
  if (reading && previous.current !== undefined) {
    if (reading.value > previous.current) direction = "up";
    else if (reading.value < previous.current) direction = "down";
  }

  return (
    <article
      data-testid={`reading-tile-${type}`}
      className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/60"
    >
      <div className="flex items-center justify-between text-sm text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-2">
          <span aria-hidden="true">{SENSOR_ICONS[type]}</span>
          <span>{SENSOR_LABELS[type]}</span>
        </span>
        {reading && (
          <span className="text-xs">
            <Trend direction={direction} />
          </span>
        )}
      </div>
      <div className="mt-2">
        {reading ? (
          <>
            <div className="text-3xl font-semibold tracking-tight">
              {formatValue(reading.value, type)}
              <span className="ml-1 text-base font-normal text-slate-500 dark:text-slate-400">
                {SENSOR_UNITS[type]}
              </span>
            </div>
            <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {formatRelative(reading.timestamp)}
            </div>
          </>
        ) : (
          <div className="text-slate-400 dark:text-slate-500">No data yet</div>
        )}
      </div>
    </article>
  );
}

export function LiveReadings() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["readings", "latest"],
    queryFn: ({ signal }) => api.latestReadings(signal),
    refetchOnWindowFocus: false,
    staleTime: 5_000,
  });

  const byType = new Map<SensorType, Reading>((data ?? []).map((r) => [r.type, r] as const));

  return (
    <Card title="Live readings">
      {isLoading && <div className="text-sm text-slate-500">Loading…</div>}
      {isError && (
        <div className="text-sm text-red-600 dark:text-red-400">
          Could not load latest readings.
        </div>
      )}
      {!isLoading && !isError && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {SENSOR_TYPES.map((type) => (
            <ReadingTile key={type} type={type} reading={byType.get(type)} />
          ))}
        </div>
      )}
    </Card>
  );
}
