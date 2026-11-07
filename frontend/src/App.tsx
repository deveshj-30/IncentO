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

const metricLabel: Record<string, string> = {
  discount: "Discount rate",
  complaint_30d: "30-day complaints",
  cancel_30d: "30-day cancellations",
};

function MetricCard({
  metric,
}: {
  metric: Investigation["analysis"]["metrics"][number];
}) {
  const monthEnd = metric.month_end_value;
  const other = metric.other_value;
  const isAvailable = monthEnd !== null && other !== null;
  const label = metricLabel[metric.name] ?? metric.name.replaceAll("_", " ");
  return (
    <article className="metric-card">
      <div className="card-topline">
        <span className="eyebrow">{label}</span>
        <span className={`signal signal-${metric.status}`}>
          {metric.status.replaceAll("_", " ")}
        </span>
      </div>
      <div className="metric-value">
        {metric.gap === null ? "—" : `${Math.round(metric.gap * 100)} points`}
        <span>gap</span>
      </div>
      {isAvailable ? (
        <div
          className="bar-chart"
          role="img"
          aria-label={`${label}: month-end ${Math.round(monthEnd * 100)} percent, other deals ${Math.round(other * 100)} percent`}
        >
          <div className="bar-row">
            <span>Month-end</span>
            <div className="bar-track">
              <div
                className="bar-fill bar-accent"
                style={{
                  width: `${Math.min(100, Math.max(0, monthEnd * 100))}%`,
                }}
              />
            </div>
            <strong>{Math.round(monthEnd * 100)}%</strong>
          </div>
          <div className="bar-row">
            <span>Other deals</span>
            <div className="bar-track">
              <div
                className="bar-fill bar-muted"
                style={{ width: `${Math.min(100, Math.max(0, other * 100))}%` }}
              />
            </div>
            <strong>{Math.round(other * 100)}%</strong>
          </div>
        </div>
      ) : (
        <p className="muted">Comparison unavailable for this window.</p>
      )}
      <div className="card-foot mono">
        {metric.month_end_n} month-end / {metric.other_n} other deals
      </div>
    </article>
  );
}

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
    <div className="app-frame">
      <div className="shell">
        <header className="site-header">
          <h1 className="brand-wordmark">IncentO</h1>
          <div className="header-meta">
            <span className="live-indicator">
              <i aria-hidden="true" /> DEMO WORKSPACE
            </span>
            <span className="badge">
              {investigation.synthetic
                ? "Synthetic data"
                : "Data status unknown"}
            </span>
          </div>
        </header>
        <nav className="main-nav" aria-label="Main navigation">
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
        <p role="status" className="status-line mono">
          <span aria-hidden="true">↳</span> {message}
        </p>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <main>
          {screen === "Overview" && (
            <section className="screen-section overview-section">
              <div className="hero-grid">
                <div className="hero-copy">
                  <span className="eyebrow section-index">
                    01 / POLICY OVERVIEW
                  </span>
                  <h2>
                    See the signal<span className="accent-stop">.</span>
                    <br />
                    Question the incentive.
                  </h2>
                  <p>
                    Investigate whether an acquisition bonus coincides with
                    heavier month-end discounting and poorer customer outcomes.
                  </p>
                  <span className="policy-tag mono">
                    ACTIVE POLICY / Acquisition bonus
                  </span>
                  <div className="hero-annotation mono">
                    <span className="annotation-line" /> MEASURED ASSOCIATION ·
                    NOT CAUSATION
                  </div>
                </div>
                <div className="hero-visual" aria-hidden="true">
                  <div className="visual-grid" />
                  <div className="visual-crosshair crosshair-one">+</div>
                  <div className="visual-crosshair crosshair-two">+</div>
                  <div className="visual-caption mono">SIGNAL / 001</div>
                  <div className="visual-bars">
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                  </div>
                  <div className="visual-rule" />
                  <div className="visual-number">
                    {analysis.flagged ? "01" : "00"}
                    <span> / FLAGGED ANALYSIS</span>
                  </div>
                </div>
              </div>
              <div className="section-heading">
                <div>
                  <span className="eyebrow">CONFIGURE ANALYSIS</span>
                  <h3>Run an investigation</h3>
                </div>
                <span className="section-caption mono">
                  DATASET / POLICY / WINDOW
                </span>
              </div>
              <div className="run-panel">
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
                          item.policy_id === policyId &&
                          item.scenario === scenario,
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
              </div>
              <div className="section-heading metrics-heading">
                <div>
                  <span className="eyebrow">AT A GLANCE</span>
                  <h3>Measured gaps</h3>
                </div>
                <span className="section-caption mono">
                  MONTH-END VS. OTHER DEALS
                </span>
              </div>
              <div className="grid metrics-grid">
                {analysis.metrics.map((item) => (
                  <MetricCard key={item.name} metric={item} />
                ))}
              </div>
              <article className="saved-runs">
                <h3>Saved investigations</h3>
                {runs.length === 0 ? (
                  <p>{runsError || "No saved runs yet."}</p>
                ) : (
                  <div className="controls">
                    <label>
                      Run
                      <select
                        value={selectedRunId}
                        onChange={(event) =>
                          setSelectedRunId(event.target.value)
                        }
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
            <section className="screen-section">
              <div className="page-intro">
                <span className="eyebrow">02 / RUN {investigation.run_id}</span>
                <h2>
                  Follow the evidence<span className="accent-stop">.</span>
                </h2>
                <p>
                  Read the measured signal alongside its sources, alternatives,
                  and recommended action.
                </p>
              </div>
              <div className="badges">
                <span className="badge">
                  Memory: {explanation.memory_status}
                </span>
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
                <div className="grid two findings-grid">
                  <article className="evidence-card">
                    <div className="card-topline">
                      <span className="eyebrow">01 / SOURCE RECORDS</span>
                      <span className="mono count">
                        {analysis.evidence.length.toString().padStart(2, "0")}{" "}
                        ITEMS
                      </span>
                    </div>
                    <h3>Evidence trail</h3>
                    {analysis.evidence.length === 0 && (
                      <p>No evidence available for this run.</p>
                    )}
                    <div className="evidence-list">
                      {analysis.evidence.map((item) => (
                        <div className="evidence-item" key={item.id}>
                          <div className="evidence-node" aria-hidden="true" />
                          <div>
                            <div className="evidence-meta mono">
                              <strong>{item.id}</strong>
                              <span>{item.source_type}</span>
                              <span>{item.timestamp.slice(0, 10)}</span>
                            </div>
                            <p>
                              {item.excerpt ??
                                "No excerpt recorded for this source."}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </article>
                  <article className="explanation-card">
                    <span className="eyebrow">02 / INTERPRETATION</span>
                    <h3>Explanation</h3>
                    <p>{explanation.hypothesis}</p>
                    <div className="action-divider" />
                    <span className="eyebrow">NEXT STEP</span>
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
            <section className="screen-section">
              <div className="page-intro">
                <span className="eyebrow">
                  03 / INCIDENT {investigation.incident_id ?? "NOT CREATED"}
                </span>
                <h2>
                  Close the loop<span className="accent-stop">.</span>
                </h2>
                <p>
                  Track the investigation, decisions, measured results, and
                  memory retention.
                </p>
              </div>
              <article className="incident-card">
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
          <span>
            IncentO <span className="footer-divider">/</span> Incentive
            intelligence
          </span>
          <span>
            {live ? "Live API result" : "Illustrative contract fixture"} ·
            Results show association, not causation.
          </span>
        </footer>
      </div>
    </div>
  );
}
