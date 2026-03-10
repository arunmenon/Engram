export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/v1";
export const HEALTH_POLL_INTERVAL = Number(
  import.meta.env.VITE_HEALTH_POLL_MS ?? 30000,
);
