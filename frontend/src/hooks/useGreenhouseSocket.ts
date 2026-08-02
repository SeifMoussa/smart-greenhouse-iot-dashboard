import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { useWebSocket, type WSStatus } from "./useWebSocket";
import type { Actuator, Alert, Reading, WSEvent } from "../types/api";

const FALLBACK_WS = "ws://localhost:8000/ws";

function getWsUrl(token: string): string {
  const base = import.meta.env.VITE_WS_URL?.trim() || FALLBACK_WS;
  // Browsers can't attach custom headers to a WebSocket handshake, so the
  // token travels as a query parameter instead — verified the same way as
  // the Bearer header everywhere else in the API.
  return `${base}?token=${encodeURIComponent(token)}`;
}

/**
 * Subscribe to the backend WebSocket and update the React Query cache
 * as events arrive:
 *  - `reading` events are prepended to `["readings", "latest"]` and
 *    `["readings", "list"]` queries.
 *  - `alert` events are prepended to `["alerts"]`.
 *  - `actuator` events update `["actuators"]`.
 */
export function useGreenhouseSocket(token: string): { status: WSStatus } {
  const queryClient = useQueryClient();

  const handler = useCallback(
    (event: WSEvent) => {
      if (event.type === "reading") {
        const reading: Reading = event.data;
        // Update latest-per-type cache.
        queryClient.setQueryData<Reading[]>(["readings", "latest"], (prev) => {
          if (!prev) return [reading];
          const filtered = prev.filter((r) => r.type !== reading.type);
          return [...filtered, reading];
        });
        // Invalidate history queries so they refetch when the user changes range.
        // Keeping it light: only mark stale, don't refetch eagerly.
        queryClient.invalidateQueries({
          queryKey: ["readings", "history"],
          refetchType: "none",
        });
      } else if (event.type === "alert") {
        const alert: Alert = event.data;
        queryClient.setQueryData<Alert[]>(["alerts"], (prev) =>
          prev ? [alert, ...prev].slice(0, 50) : [alert],
        );
      } else if (event.type === "actuator") {
        const actuator: Actuator = event.data;
        queryClient.setQueryData<Actuator[]>(["actuators"], (prev) => {
          if (!prev) return [actuator];
          return prev.map((a) => (a.id === actuator.id ? actuator : a));
        });
      }
    },
    [queryClient],
  );

  const { status } = useWebSocket<WSEvent>(getWsUrl(token), { onMessage: handler });
  return { status };
}
