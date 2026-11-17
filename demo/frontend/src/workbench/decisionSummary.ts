export interface Transition {
  sample: number; event: string; record: string; to: string; only_from: string[] | null;
}
export function relationshipChanges(before: string[][], after: string[][]) {
  return [...new Set([...before, ...after].map(edge => edge[1]))].sort().map(name => {
    const old = new Set(before.filter(edge => edge[1] === name).map(edge => JSON.stringify(edge)));
    const next = new Set(after.filter(edge => edge[1] === name).map(edge => JSON.stringify(edge)));
    return {name: name.replace(/_/g, " ").toLowerCase(), before: old.size, after: next.size,
      added: [...next].filter(edge => !old.has(edge)).length,
      removed: [...old].filter(edge => !next.has(edge)).length};
  });
}
/** Observations about supplied requests, never a simulation of accepted graph state. */
export function lifecycleComparison(before: Transition[], after: Transition[], initial?: string) {
  return after.map(next => {
    const current = before.find(row => row.sample === next.sample && row.record === next.record && row.event === next.event);
    const changedStartingStates = current?.only_from && next.only_from
      ? [...new Set([...current.only_from, ...next.only_from])].filter(state =>
          current.only_from!.includes(state) !== next.only_from!.includes(state)) : [];
    const unrepresented = changedStartingStates.filter(state => state !== initial &&
      !after.some(row => row.sample < next.sample && row.record === next.record && row.to === state));
    return {current, next, unrepresented};
  });
}
export function decisionEvidence(text: string) {
  try {
    const value = JSON.parse(text);
    if (typeof value.question === "string") return [value.question, value.effect].filter(x => typeof x === "string").join(" ");
  } catch { /* Legacy plain-text decision. */ }
  return text;
}
