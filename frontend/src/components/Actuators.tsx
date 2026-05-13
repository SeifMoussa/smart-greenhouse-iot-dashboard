import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import { type Actuator, type ActuatorId, ACTUATOR_IDS, ACTUATOR_LABELS } from "../types/api";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

const ACTUATOR_ICONS: Record<ActuatorId, string> = {
  fan: "💨",
  pump: "💧",
  light: "💡",
};

function ActuatorRow({ actuator }: { actuator: Actuator }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (next: "on" | "off") => api.setActuatorState(actuator.id, next),
    onMutate: async (next) => {
      await queryClient.cancelQueries({ queryKey: ["actuators"] });
      const previous = queryClient.getQueryData<Actuator[]>(["actuators"]);
      queryClient.setQueryData<Actuator[]>(["actuators"], (current) =>
        (current ?? []).map((a) => (a.id === actuator.id ? { ...a, state: next } : a)),
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["actuators"], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["actuators"] });
    },
  });

  const isOn = actuator.state === "on";
  return (
    <div
      data-testid={`actuator-row-${actuator.id}`}
      className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-800/60"
    >
      <div className="flex items-center gap-2">
        <span aria-hidden="true" className="text-lg">
          {ACTUATOR_ICONS[actuator.id]}
        </span>
        <div>
          <div className="text-sm font-medium">{ACTUATOR_LABELS[actuator.id]}</div>
          <div
            className={`text-xs ${isOn ? "text-leaf-600 dark:text-leaf-400" : "text-slate-500 dark:text-slate-400"}`}
            data-testid={`actuator-state-${actuator.id}`}
          >
            {isOn ? "Running" : "Idle"}
          </div>
        </div>
      </div>
      <Button
        variant={isOn ? "danger" : "primary"}
        loading={mutation.isPending}
        onClick={() => mutation.mutate(isOn ? "off" : "on")}
        aria-label={`Turn ${ACTUATOR_LABELS[actuator.id]} ${isOn ? "off" : "on"}`}
        aria-pressed={isOn}
      >
        {isOn ? "Turn off" : "Turn on"}
      </Button>
    </div>
  );
}

export function Actuators() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["actuators"],
    queryFn: ({ signal }) => api.listActuators(signal),
    refetchOnWindowFocus: false,
    staleTime: 30_000,
  });

  return (
    <Card title="Actuators">
      {isLoading && <div className="text-sm text-slate-500">Loading…</div>}
      {isError && (
        <div className="text-sm text-red-600 dark:text-red-400">Could not load actuators.</div>
      )}
      {!isLoading && !isError && (
        <div className="space-y-2">
          {ACTUATOR_IDS.map((id) => {
            const actuator = data?.find((a) => a.id === id);
            if (!actuator) return null;
            return <ActuatorRow key={id} actuator={actuator} />;
          })}
        </div>
      )}
    </Card>
  );
}
