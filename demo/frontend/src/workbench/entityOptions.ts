import type { Draft } from "./types";

export interface EntityOption {
  id: string;
  type: string;
  label: string;
  searchText?: string;
}

// IDs come from the engine's planned writes, never a second implementation of key rules.
export function sampleEntities(draft: Draft | null): EntityOption[] {
  const options = new Map<string, EntityOption>();
  const definitions = draft?.proposal?.pack?.types?.nodes || {};
  for (const sample of draft?.validation?.samples || []) {
    for (const node of sample.planned?.nodes || []) {
      const id = node.ref?.key;
      const type = node.ref?.label;
      if (!id || !type || !definitions[type]) continue;
      const props = node.properties || {};
      const keys: string[] = definitions[type].key || [];
      const identity = keys
        .map((key) => props[key])
        .filter((value) => value != null)
        .join(" / ");
      const title = props.display_name || props.name || props.title;
      const label = title ? `${title} — ${type} · ${identity || "identifier unavailable"}` : `${type} · ${identity || "Unlabelled sample entity"}`;
      const searchText = [label, props.name, props.display_name, props.title].filter(value => typeof value === "string").join(" ");
      const prior = options.get(id);
      if (!prior || title) options.set(id, { id, type, label, searchText });
    }
  }
  return [...options.values()];
}

