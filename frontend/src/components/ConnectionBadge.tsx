import type { WSStatus } from "../hooks/useWebSocket";

const STATUS_META: Record<WSStatus, { label: string; color: string }> = {
  connecting: { label: "Connecting", color: "bg-amber-400" },
  open: { label: "Live", color: "bg-leaf-500" },
  closed: { label: "Disconnected", color: "bg-slate-400" },
  error: { label: "Connection error", color: "bg-red-500" },
};

export function ConnectionBadge({ status }: { status: WSStatus }) {
  const meta = STATUS_META[status];
  return (
    <span
      role="status"
      aria-live="polite"
      className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200"
    >
      <span className={`inline-block h-2 w-2 rounded-full ${meta.color}`} aria-hidden="true" />
      {meta.label}
    </span>
  );
}
