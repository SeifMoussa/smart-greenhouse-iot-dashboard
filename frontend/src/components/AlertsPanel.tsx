import { useQuery } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import { type Alert, SENSOR_LABELS } from "../types/api";
import { Card } from "./ui/Card";

function severityClasses(severity: Alert["severity"]): string {
  if (severity === "critical") {
    return "border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200";
  }
  return "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200";
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function AlertsPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["alerts"],
    queryFn: ({ signal }) => api.listAlerts(20, signal),
    refetchOnWindowFocus: false,
    staleTime: 5_000,
  });

  return (
    <Card title="Recent alerts">
      {isLoading && <div className="text-sm text-slate-500">Loading…</div>}
      {isError && (
        <div className="text-sm text-red-600 dark:text-red-400">Could not load alerts.</div>
      )}
      {!isLoading && !isError && (data?.length ?? 0) === 0 && (
        <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
          No alerts yet. All sensors are within their configured bands.
        </div>
      )}
      {!isLoading && !isError && (data?.length ?? 0) > 0 && (
        <ul className="space-y-2" role="list">
          {data!.map((alert) => (
            <li
              key={alert.id}
              data-testid={`alert-${alert.id}`}
              className={`rounded-lg border px-3 py-2 text-sm ${severityClasses(alert.severity)}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">
                  {SENSOR_LABELS[alert.type]} · {alert.severity}
                </span>
                <span className="text-xs opacity-75">{formatTime(alert.created_at)}</span>
              </div>
              <p className="mt-1">{alert.message}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
