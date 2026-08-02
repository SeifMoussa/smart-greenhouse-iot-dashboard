/**
 * Types mirror the backend Pydantic schemas. Keep these in sync with
 * `backend/src/greenhouse/schemas.py`.
 */

export type SensorType = "temperature" | "humidity" | "soil_moisture" | "light";

export type ActuatorId = "fan" | "pump" | "light";

export type ActuatorStateValue = "on" | "off";

export type Severity = "warning" | "critical";

export const SENSOR_TYPES: readonly SensorType[] = [
  "temperature",
  "humidity",
  "soil_moisture",
  "light",
] as const;

export const ACTUATOR_IDS: readonly ActuatorId[] = ["fan", "pump", "light"] as const;

export interface Reading {
  id: number;
  sensor_id: string;
  type: SensorType;
  value: number;
  unit: string;
  timestamp: string; // ISO 8601
  created_at: string; // ISO 8601
}

export interface Threshold {
  type: SensorType;
  min_value: number;
  max_value: number;
  updated_at: string; // ISO 8601
}

export interface Alert {
  id: number;
  type: SensorType;
  value: number;
  threshold_min: number;
  threshold_max: number;
  severity: Severity;
  message: string;
  created_at: string; // ISO 8601
}

export interface Actuator {
  id: ActuatorId;
  name: string;
  state: ActuatorStateValue;
  updated_at: string; // ISO 8601
}

export interface HealthStatus {
  status: "ok";
  version: string;
  uptime_seconds: number;
}

export type Role = "viewer" | "operator";

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  role: Role;
  username: string;
}

/* WebSocket event envelopes */

export interface ReadingEvent {
  type: "reading";
  data: Reading;
}

export interface AlertEvent {
  type: "alert";
  data: Alert;
}

export interface ActuatorEvent {
  type: "actuator";
  data: Actuator;
}

export type WSEvent = ReadingEvent | AlertEvent | ActuatorEvent;

/* Display helpers */

export const SENSOR_LABELS: Record<SensorType, string> = {
  temperature: "Temperature",
  humidity: "Humidity",
  soil_moisture: "Soil Moisture",
  light: "Light",
};

export const SENSOR_UNITS: Record<SensorType, string> = {
  temperature: "°C",
  humidity: "%",
  soil_moisture: "%",
  light: "lux",
};

export const ACTUATOR_LABELS: Record<ActuatorId, string> = {
  fan: "Ventilation Fan",
  pump: "Water Pump",
  light: "Grow Light",
};
