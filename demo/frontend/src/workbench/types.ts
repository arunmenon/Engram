export interface Source {
  id: string;
  name: string;
  kind: "specification" | "schema" | "samples";
  text: string;
}
export interface Question {
  id: string;
  query: string;
  expected: string[];
  intent: string | null;
  seed_node_ids: string[];
  seed_mode?: "discover" | "explicit";
  node_type: string | null;
  reviewed: boolean;
  expectation_statement?: string | null;
}
export interface Content {
  name: string;
  environment: string;
  roots: string[];
  existing_packs: string[];
  scope: string;
  data_policy: "undecided" | "local_only" | "provider_allowed";
  redaction_confirmed: boolean;
  sources: Source[];
  decisions: Record<string, string>;
  questions: Question[];
  min_f1: number;
  expected_nodes: string[];
  forbidden_nodes: string[];
  graph_reviewed: boolean;
  producer_ids: string[];
  trusted_ids: string[];
  trust_reviewed: boolean;
  instruction: string;
}
export interface Fact {
  id: string;
  concept: string;
  explanation: string;
  basis: string;
  citations: { source_id: string; quote: string }[];
  pack_paths?: string[];
  decision_ids?: string[];
  instruction_quote?: string | null;
  trusted_producers?: string[] | null;
}
export interface Draft {
  storage_run?: { backend: string; phase: string; resource?: string; cleanup?: string };
  journey_pack_snapshot?: {primary_pack: string; packs: unknown[]};
  journey_pack_origin?: {draft_id: string; revision: number};
  journey_brief?: any;
  journey_outline?: any;
  journey_decisions?: string;
  journey_proposal?: any;
  journey_origin?: any;
  journey_coverage?: { source: string; status: string; reason: string; sites: number[] }[];
  journey?: any;
  journey_result?: any;
  journey_result_stale?: boolean;
  story_inspection?: { rows: {kind: string; label: string; status: string; occurrences: number; checks: string[]}[]; checks: {id: string; label: string; kind: string; status: string; outcome?: string; warnings: string[]; differences: string[]; guidance: {category: string; action: string; rerun: string; boundary: string}}[]; stale: boolean; pack_issue?: string | null; boundary: string };
  previous_sandbox?: {
    revision: number;
    result: NonNullable<Draft["sandbox"]>;
  };
  author_messages?: {
    role: string;
    text: string;
    status?: string;
    revision: number;
  }[];
  id: string;
  revision: number;
  content: Content;
  proposal: {
    summary: string;
    facts: Fact[];
    decisions: { id: string; question: string; effect: string }[];
    pack: Record<string, any> | null;
    limitations: string[];
    repair_removals?: string[];
  } | null;
  proposal_changes?: {
    id: string; path: string[]; category: string; kind: string; summary: string;
    before: unknown; after: unknown;
  }[];
  proposal_stale?: boolean;
  explain_stale_allowed?: boolean;
  pending_decisions?: boolean;
  review: {
    accepted_facts: string[];
    rejected_facts?: string[];
    pack_accepted: boolean;
    accepted_removals?: string[];
    accepted_changes?: string[];
    confirmed_policies?: string[];
  } | null;
  validation: {
    passed: boolean;
    problems: string[];
    inert?: string[];
    samples?: any[];
    packs?: { name: string; version: string }[];
    schema?: any;
    change?: { kind: string; reasons: string[] };
    engine_revision?: string;
    input_digest?: string;
  } | null;
  sandbox: {
    backend?: string;
    passed: boolean;
    steps: any[];
    evaluation: any;
    limits: string[];
    missing_nodes: string[];
    forbidden_nodes: string[];
    dead_letters: any[];
  } | null;
  approval: { digest: string; operator: string } | null;
  job?: { kind?: string; status: string; error?: string; attempt?: number; cancelling?: boolean } | null;
  readiness: Record<
    "begin" | "run" | "approve",
    { ready: boolean; missing: string[] }
  >;
  history: { action: string; operator: string; at: string; revision: number }[];
}
export interface Capabilities {
  packs?: string[];
  pack_catalog?: { name: string; description: string; version: string; requires: string[]; has_lifecycle: boolean }[];
  explaining?: boolean;
  operator: string;
  model: string | null;
  authoring: boolean;
  sandbox: string;
  activation: boolean;
}
export const initialContent = (name: string, environment: string): Content => ({
  name,
  environment,
  roots: [],
  existing_packs: [],
  scope: "",
  data_policy: "undecided",
  redaction_confirmed: false,
  sources: [],
  decisions: {},
  questions: [],
  min_f1: 0.8,
  expected_nodes: [],
  forbidden_nodes: [],
  graph_reviewed: false,
  producer_ids: [],
  trusted_ids: [],
  trust_reviewed: false,
  instruction: "",
});
