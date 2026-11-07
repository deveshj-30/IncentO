import { useEffect, useState } from "react";
import {
  api,
  type Incident,
  type Investigation,
  type InvestigationSummary,
  type MemoryMode,
  type PolicySummary,
} from "./api";
import { sample, sampleWithoutMemory } from "./fixtures";

type Screen = "Overview" | "Investigation" | "Incident timeline";
const errorText = (cause: unknown, fallback: string) =>
  cause instanceof Error ? cause.message : fallback;

function ComparisonCard({ run, label }: { run: Investigation; label: string }) {
  const { explanation } = run;
  return (
    <article>
      <span className="eyebrow">{label}</span>
      <h3>Memory {run.memory_mode}</h3>
      <p>
        Memory: {explanation.memory_status} · Explanation:{" "}
        {explanation.explanation_source}
      </p>
      <p>{explanation.summary}</p>
      <h4>Recommended action</h4>
      {explanation.recommendations.length === 0 && (
        <p>No recommendation available.</p>
      )}
      {explanation.recommendations.map((item, index) => (
        <p key={index}>
          <strong>{item.action_type.replaceAll("_", " ")}</strong>
          <br />
          {item.action}
          <br />
          Memory used: {item.history_influence.join(", ") || "none"}
        </p>
      ))}
      <h4>Recalled history</h4>
      {explanation.recalled.length === 0 && <p>No recalled items.</p>}
      {explanation.recalled.map((item) => (
        <p key={item.id}>
          <strong>{item.summary}</strong>
          <br />
          {item.memory_type} · {item.event_time} · {item.id}
        </p>
      ))}
    </article>
  );
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("Overview");
  const [compare, setCompare] = useState(false);
  const [policies, setPolicies] = useState<PolicySummary[]>([]);
  const [policyError, setPolicyError] = useState("");
  const [runs, setRuns] = useState<InvestigationSummary[]>([]);
  const [runsError, setRunsError] = useState("");
  const [selectedRunId, setSelectedRunId] = useState("");
  const [scenario, setScenario] = useState("risk");
  const [policyId, setPolicyId] = useState("POL-RISK-001");
  const [asOf, setAsOf] = useState("2026-11-01");
  const [memoryMode, setMemoryMode] = useState<MemoryMode>("live");
  const [investigation, setInvestigation] = useState<Investigation>(sample);
  const [comparison, setComparison] = useState<Investigation | null>(
    sampleWithoutMemory,
  );
  const [incident, setIncident] = useState<Incident | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState(
    "Showing an illustrative contract fixture. Load a scenario to use the API.",
  );
  const [live, setLive] = useState(false);
  const [outcomeType, setOutcomeType] = useState<
    "decision" | "measured_result"
  >("decision");
  const [note, setNote] = useState("");
  const { analysis, explanation } = investigation;
  const offRun =
    investigation.memory_mode === "off"
      ? investigation
      : comparison?.memory_mode === "off"
        ? comparison
        : null;
  const liveRun =
    investigation.memory_mode === "live"
      ? investigation
      : comparison?.memory_mode === "live"
        ? comparison
        : null;

  useEffect(() => {
    api
      .policies()
      .then((items) => {
        setPolicies(items);
        setPolicyError("");
      })
      .catch(() =>
        setPolicyError(
          "Policy list is unavailable. You can still load a scenario.",
        ),
      );
    api
      .investigations()
      .then(setRuns)
      .catch(() =>
        setRunsError(
          "Saved runs are unavailable. Start the backend to reopen one.",
        ),
      );
  }, []);

  function showRun(result: Investigation, status: string) {
    setInvestigation(result);
    setComparison(null);
    setIncident(null);
    setLive(true);
    setCompare(false);
    setScreen("Investigation");
    setMessage(status);
  }

  function refreshRuns() {
    api
      .investigations()
      .then((items) => {
        setRuns(items);
        setRunsError("");
      })
      .catch(() => setRunsError("Could not refresh saved runs."));
  }

  async function run() {
    setBusy(true);
    setError("");
    try {
      const loaded = await api.load(scenario);
      const selectedPolicyId = loaded.policies.includes(policyId)
        ? policyId
        : loaded.policies[0];
      if (!selectedPolicyId)
        throw new Error(`Scenario ${scenario} has no policies`);
      const result = await api.investigate(
        selectedPolicyId,
        scenario,
        `${asOf}T00:00:00Z`,
        memoryMode,
      );
      setPolicyId(selectedPolicyId);
      showRun(result, `Loaded run ${result.run_id}`);
      refreshRuns();
      api
        .policies()
        .then((items) => {
          setPolicies(items);
          setPolicyError("");
        })
        .catch(() => setPolicyError("Could not refresh the policy list."));
    } catch (cause) {
      setError(errorText(cause, "Investigation failed"));
    } finally {
      setBusy(false);
    }
  }

  async function openSavedRun() {
    if (!selectedRunId) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.investigation(selectedRunId);
      showRun(result, `Reopened saved run ${result.run_id}`);
    } catch (cause) {
      setError(errorText(cause, "Could not reopen investigation"));
    } finally {
      setBusy(false);
    }
  }

  async function runComparison() {
    if (!live) return;
    setBusy(true);
    setError("");
    try {
      const opposite: MemoryMode =
        investigation.memory_mode === "live" ? "off" : "live";
      setComparison(
        await api.investigate(
          investigation.policy_id,
          investigation.scenario,
          investigation.as_of,
          opposite,
        ),
      );
    } catch (cause) {
      setError(errorText(cause, "Could not run comparison"));
    } finally {
      setBusy(false);
    }
  }

  async function showIncident() {
    setScreen("Incident timeline");
    setError("");
    if (!live || !investigation.incident_id) return;
    try {
      setIncident(await api.incident(investigation.incident_id));
    } catch (cause) {
      setError(errorText(cause, "Could not load incident"));
    }
  }

  async function submitOutcome() {
    if (!investigation.incident_id) return;
    setBusy(true);
    setError("");
    try {
      await api.outcome(
        investigation.incident_id,
        investigation.run_id,
        outcomeType,
        new Date().toISOString(),
        note,
      );
      setIncident(await api.incident(investigation.incident_id));
      setNote("");
      setMessage("Outcome saved. Check its retention status below.");
    } catch (cause) {
      setError(errorText(cause, "Could not save outcome"));
    } finally {
      setBusy(false);
    }
  }

  async function retryRetention(id: string) {
    setBusy(true);
    setError("");
    try {
      await api.retry(id);
      if (investigation.incident_id)
        setIncident(await api.incident(investigation.incident_id));
    } catch (cause) {
      setError(errorText(cause, "Retry failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header>
        <div>
          <span className="eyebrow">REVENUE OPERATIONS · DEMO</span>
          <h1>IncentO</h1>
        </div>
        <span className="badge">
          {investigation.synthetic ? "Synthetic data" : "Data status unknown"}
        </span>
      </header>
      <nav aria-label="Main navigation">
        <button
          className={screen === "Overview" ? "active" : ""}
          onClick={() => setScreen("Overview")}
        >
          Overview
        </button>
        <button
          className={screen === "Investigation" ? "active" : ""}
          onClick={() => setScreen("Investigation")}
        >
          Investigation
        </button>
        <button
          className={screen === "Incident timeline" ? "active" : ""}
          onClick={showIncident}
        >
          Incident timeline
        </button>
      </nav>
      <p role="status">{message}</p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <main>
        {screen === "Overview" && (
          <section>
            <span className="eyebrow">POLICY OVERVIEW</span>
            <h2>Acquisition bonus</h2>
            <p>
              Review whether month-end deals show signs of poor customer fit.
            </p>
            <div className="controls">
              <label>
                Scenario
                <input
                  value={scenario}
                  onChange={(event) => {
                    const next = event.target.value;
                    setScenario(next);
                    setPolicyId(
                      policies.find((item) => item.scenario === next)
                        ?.policy_id ?? "",
                    );
                  }}
                />
              </label>
              <label>
                Policy
                <select
                  value={policyId}
                  onChange={(event) => setPolicyId(event.target.value)}
                >
                  {!policies.some(
                    (item) =>
                      item.policy_id === policyId && item.scenario === scenario,
                  ) && (
                    <option value={policyId}>
                      {policyId || "Select a policy after loading"}
                    </option>
                  )}
                  {policies
                    .filter((item) => item.scenario === scenario)
                    .map((item) => (
                      <option key={item.policy_id} value={item.policy_id}>
                        {item.name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                As of
                <input
                  type="date"
                  value={asOf}
                  onChange={(event) => setAsOf(event.target.value)}
                />
              </label>
              <label>
                Memory
                <select
                  value={memoryMode}
                  onChange={(event) =>
                    setMemoryMode(event.target.value as MemoryMode)
                  }
                >
                  <option value="live">Live</option>
                  <option value="off">Off</option>
                </select>
              </label>
            </div>
            {policyError && <p className="error">{policyError}</p>}
            <button
              className="primary"
              disabled={busy || !scenario || !asOf}
              onClick={run}
            >
              {busy ? "Running…" : "Load and investigate"}
            </button>
            <div className="grid">
              {analysis.metrics.map((item) => (
                <article key={item.name}>
                  <span className="eyebrow">
                    {item.name.replaceAll("_", " ")}
                  </span>
                  <h3>
                    {item.gap === null
                      ? "—"
                      : `${Math.round(item.gap * 100)} points`}
                  </h3>
                  <span className="badge">
                    {item.status.replaceAll("_", " ")}
                  </span>
                  <p>
                    {item.month_end_n} month-end / {item.other_n} other deals
                  </p>
                </article>
              ))}
            </div>
            <article>
              <h3>Saved investigations</h3>
              {runs.length === 0 ? (
                <p>{runsError || "No saved runs yet."}</p>
              ) : (
                <div className="controls">
                  <label>
                    Run
                    <select
                      value={selectedRunId}
                      onChange={(event) => setSelectedRunId(event.target.value)}
                    >
                      <option value="">Select a run</option>
                      {runs.map((item) => (
                        <option key={item.run_id} value={item.run_id}>
                          {item.run_id} · {item.scenario} · {item.memory_mode}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    disabled={busy || !selectedRunId}
                    onClick={openSavedRun}
                  >
                    Open saved run
                  </button>
                </div>
              )}
            </article>
          </section>
        )}
        {screen === "Investigation" && (
          <section>
            <span className="eyebrow">RUN {investigation.run_id}</span>
            <h2>Investigation</h2>
            <div className="badges">
              <span className="badge">Memory: {explanation.memory_status}</span>
              <span className="badge">
                Explanation: {explanation.explanation_source}
              </span>
              <span className="badge">
                As of {new Date(investigation.as_of).toLocaleDateString()}
              </span>
            </div>
            <div className="tabs">
              <button
                className={!compare ? "active" : ""}
                onClick={() => setCompare(false)}
              >
                Findings
              </button>
              <button
                className={compare ? "active" : ""}
                onClick={() => setCompare(true)}
              >
                Compare memory
              </button>
            </div>
            {compare ? (
              <>
                {live && !comparison && (
                  <button
                    className="primary"
                    disabled={busy}
                    onClick={runComparison}
                  >
                    {busy
                      ? "Running…"
                      : `Run with memory ${investigation.memory_mode === "live" ? "off" : "live"}`}
                  </button>
                )}
                {offRun && liveRun && (
                  <p>
                    Analysis{" "}
                    {offRun.analysis_digest === liveRun.analysis_digest
                      ? "matches across modes"
                      : "differs across modes"}
                    .
                  </p>
                )}
                <div className="grid two">
                  {offRun && (
                    <ComparisonCard run={offRun} label="WITHOUT MEMORY" />
                  )}
                  {liveRun && (
                    <ComparisonCard run={liveRun} label="WITH MEMORY" />
                  )}
                </div>
              </>
            ) : (
              <div className="grid two">
                <article>
                  <h3>Evidence</h3>
                  {analysis.evidence.length === 0 && (
                    <p>No evidence available for this run.</p>
                  )}
                  {analysis.evidence.map((item) => (
                    <p key={item.id}>
                      <strong>{item.id}</strong> · {item.source_type}
                      <br />
                      {item.excerpt ?? "No excerpt"}
                    </p>
                  ))}
                </article>
                <article>
                  <h3>Explanation</h3>
                  <p>{explanation.hypothesis}</p>
                  <h3>Proposed action</h3>
                  {explanation.recommendations.length === 0 && (
                    <p>No recommendation available.</p>
                  )}
                  {explanation.recommendations.map((item, index) => (
                    <p key={index}>
                      {item.action}
                      <br />
                      <small>{item.rationale}</small>
                    </p>
                  ))}
                </article>
              </div>
            )}
          </section>
        )}
        {screen === "Incident timeline" && (
          <section>
            <span className="eyebrow">
              INCIDENT {investigation.incident_id ?? "NOT CREATED"}
            </span>
            <h2>Incident timeline</h2>
            <article>
              <h3>Investigation run</h3>
              <p>
                {investigation.created_at} · {investigation.run_id}
              </p>
              {live && !investigation.incident_id && (
                <p>No incident was created for this investigation.</p>
              )}
              {incident && incident.outcomes.length === 0 && (
                <p>No outcomes recorded yet.</p>
              )}
              {incident?.outcomes.map((item) => (
                <p key={item.outcome_id}>
                  <strong>{item.type}</strong> · {item.event_time}
                  <br />
                  {item.note}
                  <br />
                  Retention: {item.retention_status}
                  {item.retention_error && ` (${item.retention_error})`}{" "}
                  {item.retention_status !== "retained" && (
                    <button
                      disabled={busy}
                      onClick={() => retryRetention(item.outcome_id)}
                    >
                      Retry retention
                    </button>
                  )}
                </p>
              ))}
              {!live && <p>Load an investigation to record an outcome.</p>}
            </article>
            {live && investigation.incident_id && (
              <article>
                <h3>Record outcome</h3>
                <label>
                  Type
                  <select
                    value={outcomeType}
                    onChange={(event) =>
                      setOutcomeType(
                        event.target.value as "decision" | "measured_result",
                      )
                    }
                  >
                    <option value="decision">Decision</option>
                    <option value="measured_result">Measured result</option>
                  </select>
                </label>
                <label>
                  Note
                  <textarea
                    maxLength={280}
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                  />
                </label>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={submitOutcome}
                >
                  Save outcome
                </button>
              </article>
            )}
          </section>
        )}
      </main>
      <footer>
        {live ? "Live API result" : "Illustrative contract fixture"} · Results
        show association, not causation.
      </footer>
    </div>
  );
}
