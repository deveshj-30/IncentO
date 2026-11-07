import type { components } from "./types/contracts";

export type Investigation = components["schemas"]["Investigation"];
export type InvestigationSummary =
  components["schemas"]["InvestigationSummary"];
export type Incident = components["schemas"]["Incident"];
export type PolicySummary = components["schemas"]["PolicySummary"];
export type Outcome = components["schemas"]["Outcome"];
export type MemoryMode = components["schemas"]["MemoryMode"];

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error("Cannot reach the API. Start the backend and try again.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.message ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  policies: () => request<PolicySummary[]>("/policies"),
  investigations: () => request<InvestigationSummary[]>("/investigations"),
  investigation: (id: string) =>
    request<Investigation>(`/investigations/${encodeURIComponent(id)}`),
  load: (scenario: string) =>
    request<components["schemas"]["DemoLoadResponse"]>("/demo/load", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    }),
  investigate: (
    policy_id: string,
    scenario: string,
    as_of: string,
    memory_mode: MemoryMode,
  ) =>
    request<Investigation>("/investigations", {
      method: "POST",
      body: JSON.stringify({
        policy_id,
        scenario,
        as_of,
        memory_mode,
        idempotency_key: crypto.randomUUID(),
      }),
    }),
  incident: (id: string) =>
    request<Incident>(`/incidents/${encodeURIComponent(id)}`),
  outcome: (
    id: string,
    run_id: string,
    type: "decision" | "measured_result",
    event_time: string,
    note: string,
  ) =>
    request<Outcome>(`/incidents/${encodeURIComponent(id)}/outcomes`, {
      method: "POST",
      body: JSON.stringify({
        type,
        run_id,
        event_time,
        note,
        idempotency_key: crypto.randomUUID(),
      }),
    }),
  retry: (id: string) =>
    request<Outcome>(`/outcomes/${encodeURIComponent(id)}/retention`, {
      method: "POST",
    }),
};
