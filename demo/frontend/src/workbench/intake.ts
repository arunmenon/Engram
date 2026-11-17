import type { Source } from "./types";

export function suggestCategory(text: string): {kind: Source["kind"] | null; reason: string} {
  if (!text.trim()) return {kind: null, reason: "Add material to see a category suggestion."};
  let value: any;
  try { value = JSON.parse(text); }
  catch { return {kind: "specification", reason: "This looks like written material. If it is an event or schema, correct the JSON before choosing that category."}; }
  const rows = Array.isArray(value) ? value : [value];
  if (rows.length && rows.every(row => row && typeof row.event_type === "string" && row.payload && typeof row.payload === "object" && !Array.isArray(row.payload))) {
    return {kind: "samples", reason: "Each record has an event name and a payload object."};
  }
  if (value && !Array.isArray(value) && typeof value === "object" && (value.$schema || value.openapi || value.swagger || (value.type === "object" && value.properties))) {
    return {kind: "schema", reason: "This contains schema declarations describing available fields."};
  }
  return {kind: null, reason: "This JSON does not clearly identify events or a schema. Choose its category; nothing has been changed."};
}

export const sourceLabels = {specification: "Process document / glossary", schema: "Interface schema (JSON)", samples: "Sample events (JSON)"};
