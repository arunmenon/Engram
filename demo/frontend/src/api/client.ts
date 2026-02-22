export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type RequestInterceptor = (url: string, method: string, body?: unknown) => void;
type ResponseInterceptor = (
  url: string,
  method: string,
  status: number,
  body: unknown,
  durationMs: number,
) => void;

const requestInterceptors: RequestInterceptor[] = [];
const responseInterceptors: ResponseInterceptor[] = [];

export function onRequest(fn: RequestInterceptor) {
  requestInterceptors.push(fn);
}

export function onResponse(fn: ResponseInterceptor) {
  responseInterceptors.push(fn);
}

async function apiFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const method = options.method ?? 'GET';
  const body = options.body ? JSON.parse(options.body as string) : undefined;

  for (const fn of requestInterceptors) fn(url, method, body);

  const start = Date.now();
  const response = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  const durationMs = Date.now() - start;

  let responseBody: unknown;
  try {
    responseBody = await response.json();
  } catch {
    // Non-JSON response (e.g. 502 HTML error page)
    responseBody = { error: `Non-JSON response (${response.status})` };
  }

  for (const fn of responseInterceptors) fn(url, method, response.status, responseBody, durationMs);

  if (!response.ok) {
    throw new ApiError(response.status, `${method} ${url} failed`, responseBody);
  }

  return responseBody as T;
}

export async function apiGet<T>(url: string): Promise<T> {
  return apiFetch<T>(url);
}

export async function apiPost<T>(url: string, body: unknown): Promise<T> {
  return apiFetch<T>(url, { method: 'POST', body: JSON.stringify(body) });
}
