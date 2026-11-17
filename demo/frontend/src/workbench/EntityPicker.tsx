import { useState } from "react";
import type { EntityOption } from "./entityOptions";
export { sampleEntities } from "./entityOptions";

export function EntityPicker({
  label,
  options,
  selected,
  onChange,
  disabled = false,
}: {
  label: string;
  options: EntityOption[];
  selected: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
}) {
  const [search, setSearch] = useState("");
  const filtered = options.filter((option) =>
    (option.searchText || option.label).toLowerCase().includes(search.trim().toLowerCase()),
  );
  const unresolved = selected.filter(
    (id) => !options.some((option) => option.id === id),
  );
  return (
    <fieldset className="wb-entity-picker" disabled={disabled}>
      <legend>{label}</legend>
      {label === "Start from these entities" && (
        <p className="wb-muted">
          These are starting points, not scope filters. The engine may also find
          entities mentioned in the question.
        </p>
      )}
      <p className="wb-muted">
        Choose entities from the sample projection. These are candidates, not
        automatically accepted answers.
      </p>
      {options.length ? (
        <>
          <label>
            Search {label.toLowerCase()}
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search names, titles or identifiers"
            />
          </label>
          <div className="wb-entity-options">
            {filtered.map((option) => (
              <label key={option.id} className="wb-checkbox">
                <input
                  type="checkbox"
                  checked={selected.includes(option.id)}
                  onChange={(e) =>
                    onChange(
                      e.target.checked
                        ? [...selected, option.id]
                        : selected.filter((id) => id !== option.id),
                    )
                  }
                />
                {option.label}
              </label>
            ))}
          </div>
          {!filtered.length && <p>No matching sample entities.</p>}
        </>
      ) : (
        <p>
          {selected.length ? `${selected.length} selections are saved. Their readable preview will return when the pack is validated.` : "Generate and validate a pack to discover selectable sample entities. You can write the question first."}
        </p>
      )}
      {options.length > 0 && unresolved.length > 0 && (
        <p role="status">
          {unresolved.length} saved selection(s) are not in this proposal’s
          sample entities. Review the technical IDs before accepting the answer.
        </p>
      )}
    </fieldset>
  );
}
