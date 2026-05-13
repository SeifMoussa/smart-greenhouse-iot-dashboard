import { useGreenhouseSocket } from "../hooks/useGreenhouseSocket";
import { Actuators } from "../components/Actuators";
import { AlertsPanel } from "../components/AlertsPanel";
import { ConnectionBadge } from "../components/ConnectionBadge";
import { ExportPanel } from "../components/ExportPanel";
import { HistoryChart } from "../components/HistoryChart";
import { LiveReadings } from "../components/LiveReadings";
import { ThemeToggle } from "../components/ThemeToggle";
import { ThresholdsForm } from "../components/ThresholdsForm";

export function Dashboard() {
  const { status } = useGreenhouseSocket();

  return (
    <div className="mx-auto flex min-h-full max-w-7xl flex-col gap-4 p-4 sm:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">🌱 Smart Greenhouse</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Real-time monitoring, alerts, and control.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ConnectionBadge status={status} />
          <ThemeToggle />
        </div>
      </header>

      <LiveReadings />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <HistoryChart />
        </div>
        <AlertsPanel />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Actuators />
        <ExportPanel />
      </div>

      <ThresholdsForm />

      <footer className="pt-2 text-center text-xs text-slate-400 dark:text-slate-500">
        Smart Greenhouse · v0.1.0 · lab-only demonstration
      </footer>
    </div>
  );
}
