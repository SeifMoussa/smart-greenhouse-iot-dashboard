import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api } from "../api/endpoints";
import {
  type SensorType,
  type Threshold,
  SENSOR_LABELS,
  SENSOR_TYPES,
  SENSOR_UNITS,
} from "../types/api";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

interface FormState {
  min: string;
  max: string;
  error?: string;
  feedback?: "saved" | "saving";
}

function validateThreshold(minStr: string, maxStr: string): { min: number; max: number } | string {
  const min = Number(minStr);
  const max = Number(maxStr);
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return "Both values must be numbers.";
  }
  if (min >= max) {
    return "Minimum must be strictly less than maximum.";
  }
  return { min, max };
}

function ThresholdRow({
  sensorType,
  threshold,
  initialMin,
  initialMax,
}: {
  sensorType: SensorType;
  threshold?: Threshold;
  initialMin: number;
  initialMax: number;
}) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<FormState>({
    min: String(initialMin),
    max: String(initialMax),
  });

  const mutation = useMutation({
    mutationFn: (payload: { min_value: number; max_value: number }) =>
      api.updateThreshold(sensorType, payload),
    onMutate: () => setState((s) => ({ ...s, feedback: "saving", error: undefined })),
    onSuccess: (updated) => {
      queryClient.setQueryData<Threshold[]>(["thresholds"], (prev) => {
        if (!prev) return [updated];
        return prev.map((t) => (t.type === sensorType ? updated : t));
      });
      setState((s) => ({ ...s, feedback: "saved" }));
    },
    onError: (err) =>
      setState((s) => ({
        ...s,
        feedback: undefined,
        error: err instanceof Error ? err.message : "Update failed.",
      })),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const validation = validateThreshold(state.min, state.max);
    if (typeof validation === "string") {
      setState((s) => ({ ...s, error: validation, feedback: undefined }));
      return;
    }
    mutation.mutate({ min_value: validation.min, max_value: validation.max });
  }

  const unit = SENSOR_UNITS[sensorType];

  return (
    <form
      onSubmit={onSubmit}
      data-testid={`threshold-form-${sensorType}`}
      className="grid grid-cols-1 items-end gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-800/60 md:grid-cols-[2fr_repeat(2,1fr)_auto]"
    >
      <div>
        <div className="text-sm font-medium">{SENSOR_LABELS[sensorType]}</div>
        {threshold && (
          <div className="text-xs text-slate-500 dark:text-slate-400">
            Current: {threshold.min_value} – {threshold.max_value} {unit}
          </div>
        )}
      </div>
      <label className="block text-xs text-slate-600 dark:text-slate-400">
        Min ({unit})
        <input
          type="number"
          step="any"
          aria-label={`Minimum ${SENSOR_LABELS[sensorType]}`}
          value={state.min}
          onChange={(e) => setState((s) => ({ ...s, min: e.target.value, error: undefined }))}
          className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
        />
      </label>
      <label className="block text-xs text-slate-600 dark:text-slate-400">
        Max ({unit})
        <input
          type="number"
          step="any"
          aria-label={`Maximum ${SENSOR_LABELS[sensorType]}`}
          value={state.max}
          onChange={(e) => setState((s) => ({ ...s, max: e.target.value, error: undefined }))}
          className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
        />
      </label>
      <Button
        type="submit"
        variant="primary"
        loading={mutation.isPending}
        aria-label={`Save threshold for ${SENSOR_LABELS[sensorType]}`}
      >
        Save
      </Button>
      {state.error && (
        <p role="alert" className="md:col-span-4 text-xs text-red-600 dark:text-red-400">
          {state.error}
        </p>
      )}
      {state.feedback === "saved" && !state.error && (
        <p className="md:col-span-4 text-xs text-leaf-600 dark:text-leaf-400">Saved ✓</p>
      )}
    </form>
  );
}

export function ThresholdsForm() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["thresholds"],
    queryFn: ({ signal }) => api.listThresholds(signal),
    refetchOnWindowFocus: false,
    staleTime: 60_000,
  });

  return (
    <Card title="Thresholds">
      {isLoading && <div className="text-sm text-slate-500">Loading…</div>}
      {isError && (
        <div className="text-sm text-red-600 dark:text-red-400">Could not load thresholds.</div>
      )}
      {!isLoading && !isError && (
        <div className="space-y-2">
          {SENSOR_TYPES.map((sensorType) => {
            const threshold = data?.find((t) => t.type === sensorType);
            return (
              <ThresholdRow
                key={sensorType}
                sensorType={sensorType}
                threshold={threshold}
                initialMin={threshold?.min_value ?? 0}
                initialMax={threshold?.max_value ?? 100}
              />
            );
          })}
        </div>
      )}
    </Card>
  );
}
