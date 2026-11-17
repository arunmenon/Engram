import { useEffect, useState } from "react";

type SampleRecord = {event_type: string; payload: Record<string, unknown>; source_name: string; number: number};
const displayValue = (value: unknown): string => value === null ? "empty (null)" : value === "" ? "empty text" : typeof value === "object" ? JSON.stringify(value) : String(value);

type Inventory = {
  sample_records?: SampleRecord[];
  sample_count: number;
  events: {event_type: string; count: number}[];
  fields: {event_type: string; field: string; records: number; present: number; missing: number; empty: number; distinct: number; repeated: number}[];
  note: string;
};

export function IntakeEvidence({revision, load, dirty}: {revision: number; load: () => Promise<Inventory>; dirty: boolean}) {
  const [data, setData] = useState<Inventory | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  useEffect(() => {
    let current = true;
    setData(null); setError(false);
    load().then(value => {if (current) setData(value);}).catch(() => {if (current) setError(true);});
    return () => {current = false;};
    // The saved revision, not each polling object, determines the inventory.
  }, [revision]);
  const needle = query.trim().toLowerCase();
  const records = data?.sample_records || [];
  const matchesField = (event: string, field: string) => !needle || event.toLowerCase().includes(needle) || field.toLowerCase().includes(needle) || records.some(record => record.event_type === event && field in record.payload && displayValue(record.payload[field]).toLowerCase().includes(needle));
  const visibleEvents = data?.events.filter(event => !needle || event.event_type.toLowerCase().includes(needle) || data.fields.some(field => field.event_type === event.event_type && matchesField(event.event_type, field.field))) || [];
  const repeats = (event: string, field: string) => {
    const grouped = new Map<string, SampleRecord[]>();
    for (const record of records.filter(record => record.event_type === event && field in record.payload)) {
      const key = JSON.stringify(record.payload[field]);
      grouped.set(key, [...(grouped.get(key) || []), record]);
    }
    return [...grouped.values()].filter(group => group.length > 1);
  };
  return <section className="wb-card" aria-label="Sample inventory">
    <h2>What your samples contain</h2>
    <p>Calculated from saved sample events, without sending material to the agent. This describes examples, not a validated pack.</p>
    {dirty && <p role="status">Save your changes to refresh these observations.</p>}
    {error ? <p role="alert">The saved samples could not be inspected. Check their category and JSON, then save again.</p> : !data ? <p role="status">Reading saved samples…</p> : <>
      <p>Sample events: {data.sample_count} · Event types: {data.events.length}</p>
      <p>{data.note}</p>
      {!data.sample_count ? <p>Add sample events to see which fields are present or missing. Written rules alone do not establish event field names.</p> : <>
        <label>Find an event, field or value<input value={query} onChange={e => setQuery(e.target.value)} /></label>
        {!visibleEvents.length && <p role="status">No samples match “{query}”. Try another event, field or value.</p>}
        {visibleEvents.map(event => <details key={event.event_type} open={needle ? true : undefined}>
          <summary>{event.event_type} · {event.count} examples</summary>
          <p>These are top-level payload fields. Distinct values include any empty values. Use these observations when deciding which fields identify a record. A repeated value can be an update to the same record or a collision; the samples alone cannot decide.</p>
          <ul>{data.fields.filter(field => field.event_type === event.event_type && matchesField(event.event_type, field.field)).map(field => <li key={field.field}>
            <strong>{field.field}</strong>: {field.present} present, {field.missing} missing, {field.empty} empty. Distinct present values: {field.distinct}; repeats: {field.repeated}.
            {repeats(event.event_type, field.field).map((group, index) => <details key={index}>
              <summary>Repeated value: {displayValue(group[0].payload[field.field])} · {group.length} occurrences</summary>
              <ul>{group.map((record, index) => <li key={index}>
                <strong>{record.source_name} · example {record.number}</strong>
                <dl>{Object.entries(record.payload).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{displayValue(value)}</dd></div>)}</dl>
              </li>)}</ul>
            </details>)}
          </li>)}</ul>
        </details>)}
      </>}
    </>}
  </section>;
}
