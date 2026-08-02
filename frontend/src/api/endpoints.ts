import { apiRequest } from "./client";
import type {
  Actuator,
  ActuatorId,
  ActuatorStateValue,
  Alert,
  HealthStatus,
  LoginResponse,
  Reading,
  SensorType,
  Threshold,
} from "../types/api";

export const api = {
  health: (signal?: AbortSignal) => apiRequest<HealthStatus>("/api/health", { signal }),

  login: (username: string, password: string) =>
    apiRequest<LoginResponse>("/api/auth/login", {
      method: "POST",
      body: { username, password },
    }),

  latestReadings: (signal?: AbortSignal) =>
    apiRequest<Reading[]>("/api/readings/latest", { signal }),

  listReadings: (
    params: { type?: SensorType; from?: string; to?: string; limit?: number } = {},
    signal?: AbortSignal,
  ) => {
    const search = new URLSearchParams();
    if (params.type) search.set("type", params.type);
    if (params.from) search.set("from", params.from);
    if (params.to) search.set("to", params.to);
    if (params.limit !== undefined) search.set("limit", String(params.limit));
    const qs = search.toString();
    return apiRequest<Reading[]>(`/api/readings${qs ? `?${qs}` : ""}`, { signal });
  },

  listThresholds: (signal?: AbortSignal) => apiRequest<Threshold[]>("/api/thresholds", { signal }),

  updateThreshold: (sensorType: SensorType, payload: { min_value: number; max_value: number }) =>
    apiRequest<Threshold>(`/api/thresholds/${sensorType}`, {
      method: "PUT",
      body: payload,
    }),

  listAlerts: (limit = 50, signal?: AbortSignal) =>
    apiRequest<Alert[]>(`/api/alerts?limit=${limit}`, { signal }),

  listActuators: (signal?: AbortSignal) => apiRequest<Actuator[]>("/api/actuators", { signal }),

  setActuatorState: (actuatorId: ActuatorId, state: ActuatorStateValue) =>
    apiRequest<Actuator>(`/api/actuators/${actuatorId}/state`, {
      method: "POST",
      body: { state },
    }),
};
