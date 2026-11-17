import { useId, useState } from "react";

type Node = { id: string; type: string; properties?: Record<string, unknown> };
type Edge = { source: string; target: string; type: string };

function nodeLabel(node: Node): string {
  const props = node.properties || {};
  const label = [props.title, props.name, props.statement].find(
    (value) => typeof value === "string" && value.length > 0,
  );
  if (typeof label === "string") return label;
  if (typeof props.verdict === "string" && typeof props.reviewer === "string") {
    return `${props.verdict} · ${props.reviewer}`;
  }
  return node.id;
}

/** Bounded SVG view over schema definitions or real stored rows, never a simulated graph. */
export function PackGraph({
  nodes,
  edges,
  mode,
}: {
  nodes: Node[];
  edges: Edge[];
  mode: "schema" | "observed";
}) {
  const marker = `arrow-${useId().replace(/:/g, "")}`;
  const [selected, setSelected] = useState<string | null>(null);
  const shown = nodes.slice(0, 12);
  const positions = new Map(
    shown.map((node, index) => [
      node.id,
      { x: 40 + (index % 2) * 370, y: 35 + Math.floor(index / 2) * 160 },
    ]),
  );
  const visibleEdges = edges
    .filter((edge) => positions.has(edge.source) && positions.has(edge.target))
    .slice(0, 30);
  const active = shown.find((node) => node.id === selected);
  const height = Math.max(160, Math.ceil(shown.length / 2) * 160);
  if (!shown.length) return <p>No domain nodes in this view yet.</p>;
  return (
    <figure className="wb-graph">
      <figcaption>
        {mode === "schema"
          ? "Schema · allowed relationships"
          : "Observed · stored domain relationships"}
        <span>
          {shown.length} nodes · {visibleEdges.length} edges
        </span>
      </figcaption>
      <svg
        viewBox={`0 0 720 ${height}`}
        role="group"
        aria-label={`${mode} graph; select a node for details`}
      >
        <defs>
          <marker
            id={marker}
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#6b8d79" />
          </marker>
        </defs>
        {visibleEdges.map((edge, index) => {
          const a = positions.get(edge.source)!,
            b = positions.get(edge.target)!;
          const x1 = a.x + 120,
            y1 = a.y + 68,
            x2 = b.x + 120,
            y2 = b.y + 15;
          const horizontal = a.y === b.y;
          const startX = horizontal ? a.x + (a.x < b.x ? 240 : 0) : x1;
          const endX = horizontal ? b.x + (a.x < b.x ? 0 : 240) : x2;
          const startY = horizontal ? a.y + 40 : y1,
            endY = horizontal ? b.y + 40 : y2;
          return (
            <g
              key={`${edge.source}-${edge.type}-${edge.target}-${index}`}
              opacity={
                !selected || [edge.source, edge.target].includes(selected)
                  ? 1
                  : 0.25
              }
            >
              <path
                d={`M${startX},${startY} C${startX},${startY + 20} ${endX},${endY - 20} ${endX},${endY}`}
                fill="none"
                stroke="#6b8d79"
                strokeWidth="1.5"
                markerEnd={`url(#${marker})`}
              />
              <text
                x={(startX + endX) / 2}
                y={(startY + endY) / 2 - 9}
                textAnchor="middle"
                fontSize="9"
                fill="#41634e"
                stroke="#f7faf6"
                strokeWidth="4"
                paintOrder="stroke"
              >
                {edge.type}
              </text>
            </g>
          );
        })}
        {shown.map((node) => {
          const p = positions.get(node.id)!;
          const label = nodeLabel(node);
          const version = node.properties?.version;
          return (
            <g
              key={node.id}
              role="button"
              tabIndex={0}
              aria-label={`Inspect ${label}${version ? ` · revision ${version}` : ""} (${node.id})`}
              aria-pressed={selected === node.id}
              onClick={() => setSelected(node.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setSelected(node.id);
                }
              }}
            >
              <title>{label} · {node.id}</title>
              <rect
                x={p.x}
                y={p.y}
                width={240}
                height={78}
                rx={9}
                fill={selected === node.id ? "#e3efe3" : "white"}
                stroke={selected === node.id ? "#1a6550" : "#c4d5c7"}
              />
              <text x={p.x + 15} y={p.y + 26} fontSize="10" fill="#6a7d6e">
                {node.type}{version ? ` · revision ${version}` : ""}
              </text>
              <text
                x={p.x + 15}
                y={p.y + 51}
                fontSize="12"
                fontWeight="600"
                fill="#244934"
              >
                {label.length > 31 ? `${label.slice(0, 28)}…` : label}
              </text>
            </g>
          );
        })}
      </svg>
      {nodes.length > shown.length && (
        <p className="wb-muted">
          Showing the first 12 nodes. The tables below contain the full result.
        </p>
      )}
      {active && (
        <div className="wb-graph-detail">
          <strong>{nodeLabel(active)}</strong>
          <dl>{Object.entries(active.properties || { type: active.type })
            .filter(([name]) => !["node_id", "ontology_version"].includes(name))
            .map(([name, value]) => <div key={name}>
              <dt>{name.replace(/_/g, " ")}</dt>
              <dd>{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd>
            </div>)}</dl>
          <details><summary>For engineers · stored record</summary>
            <p><code>{active.id}</code></p>
            <pre>{JSON.stringify(active.properties || { type: active.type }, null, 2)}</pre>
          </details>
        </div>
      )}
      <p className="wb-muted">
        Select a node or use Tab and Enter. The details below provide the same
        node and relationship data.
      </p>
    </figure>
  );
}
