import { useEffect, useState } from 'react'
import { api, type Incident, type Investigation, type PolicySummary } from './api'
import fixture from '../../contracts/examples/investigation-response.json'

type Screen = 'Overview' | 'Investigation' | 'Incident timeline'
const sample = fixture as Investigation

export default function App() {
  const [screen, setScreen] = useState<Screen>('Overview')
  const [compare, setCompare] = useState(false)
  const [policies, setPolicies] = useState<PolicySummary[]>([])
  const [scenario, setScenario] = useState('risk')
  const [policyId, setPolicyId] = useState('POL-RISK-001')
  const [asOf, setAsOf] = useState('2026-11-01')
  const [memoryMode, setMemoryMode] = useState<'live' | 'off'>('live')
  const [investigation, setInvestigation] = useState<Investigation>(sample)
  const [incident, setIncident] = useState<Incident | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('Showing an illustrative contract fixture. Load a scenario to use the API.')
  const [live, setLive] = useState(false)
  const [outcomeType, setOutcomeType] = useState<'decision' | 'measured_result'>('decision')
  const [note, setNote] = useState('')
  const { analysis, explanation } = investigation

  useEffect(() => {
    api.policies().then(setPolicies).catch(() => undefined)
  }, [])

  async function run() {
    setBusy(true); setError('')
    try {
      const loaded = await api.load(scenario)
      const selectedPolicyId = loaded.policies.includes(policyId) ? policyId : loaded.policies[0]
      if (!selectedPolicyId) throw new Error(`Scenario ${scenario} has no policies`)
      const result = await api.investigate(selectedPolicyId, scenario, `${asOf}T00:00:00Z`, memoryMode)
      setPolicyId(selectedPolicyId)
      setInvestigation(result); setLive(true); setIncident(null); setScreen('Investigation')
      setMessage(`Loaded run ${result.run_id}`)
      api.policies().then(setPolicies).catch(() => undefined)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Investigation failed') }
    finally { setBusy(false) }
  }

  async function showIncident() {
    setScreen('Incident timeline'); setError('')
    if (!live || !investigation.incident_id) return
    try { setIncident(await api.incident(investigation.incident_id)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not load incident') }
  }

  async function submitOutcome() {
    if (!investigation.incident_id) return
    setBusy(true); setError('')
    try {
      await api.outcome(investigation.incident_id, investigation.run_id, outcomeType, new Date().toISOString(), note)
      setIncident(await api.incident(investigation.incident_id))
      setNote(''); setMessage('Outcome saved. Check its retention status below.')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save outcome') }
    finally { setBusy(false) }
  }

  async function retryRetention(id: string) {
    setBusy(true); setError('')
    try {
      await api.retry(id)
      if (investigation.incident_id) setIncident(await api.incident(investigation.incident_id))
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Retry failed') }
    finally { setBusy(false) }
  }

  return <div className="shell">
    <header><div><span className="eyebrow">REVENUE OPERATIONS · DEMO</span><h1>IncentiveTrap</h1></div><span className="badge">Synthetic data</span></header>
    <nav aria-label="Main navigation"><button className={screen === 'Overview' ? 'active' : ''} onClick={() => setScreen('Overview')}>Overview</button><button className={screen === 'Investigation' ? 'active' : ''} onClick={() => setScreen('Investigation')}>Investigation</button><button className={screen === 'Incident timeline' ? 'active' : ''} onClick={showIncident}>Incident timeline</button></nav>
    <p role="status">{message}</p>{error && <p role="alert" className="error">{error}</p>}
    <main>
      {screen === 'Overview' && <section><span className="eyebrow">POLICY OVERVIEW</span><h2>Acquisition bonus</h2><p>Review whether month-end deals show signs of poor customer fit.</p><div className="controls"><label>Scenario<input value={scenario} onChange={event => { const next = event.target.value; setScenario(next); setPolicyId(policies.find(policy => policy.scenario === next)?.policy_id ?? '') }} /></label><label>Policy<select value={policyId} onChange={event => setPolicyId(event.target.value)}>{!policies.some(policy => policy.policy_id === policyId && policy.scenario === scenario) && <option value={policyId}>{policyId || 'Select a policy after loading'}</option>}{policies.filter(policy => policy.scenario === scenario).map(policy => <option key={policy.policy_id} value={policy.policy_id}>{policy.name}</option>)}</select></label><label>As of<input type="date" value={asOf} onChange={event => setAsOf(event.target.value)} /></label><label>Memory<select value={memoryMode} onChange={event => setMemoryMode(event.target.value as 'live' | 'off')}><option value="live">Live</option><option value="off">Off</option></select></label></div><button className="primary" disabled={busy} onClick={run}>{busy ? 'Running…' : 'Load and investigate'}</button><div className="grid">{analysis.metrics.map(metric => <article key={metric.name}><span className="eyebrow">{metric.name.replaceAll('_', ' ')}</span><h3>{metric.gap === null ? '—' : `${Math.round(metric.gap * 100)} points`}</h3><span className="badge">{metric.status.replaceAll('_', ' ')}</span><p>{metric.month_end_n} month-end / {metric.other_n} other deals</p></article>)}</div></section>}
      {screen === 'Investigation' && <section><span className="eyebrow">RUN {investigation.run_id}</span><h2>Investigation</h2><div className="badges"><span className="badge">Memory: {explanation.memory_status}</span><span className="badge">Explanation: {explanation.explanation_source}</span><span className="badge">As of {new Date(investigation.as_of).toLocaleDateString()}</span></div><div className="tabs"><button className={!compare ? 'active' : ''} onClick={() => setCompare(false)}>Findings</button><button className={compare ? 'active' : ''} onClick={() => setCompare(true)}>Compare memory</button></div>{compare ? <article><h3>What memory contributed</h3><p>Mode: {investigation.memory_mode}. {explanation.recalled.length} recalled item(s).</p>{explanation.recalled.map(memory => <p key={memory.id}><strong>{memory.summary}</strong><br />{memory.memory_type} · {memory.event_time} · {memory.id}</p>)}{explanation.recommendations.map((recommendation, index) => <p key={index}>Recommendation {index + 1} used: {recommendation.history_influence.join(', ') || 'no memory'}</p>)}</article> : <div className="grid two"><article><h3>Evidence</h3>{analysis.evidence.map(evidence => <p key={evidence.id}><strong>{evidence.id}</strong> · {evidence.source_type}<br />{evidence.excerpt ?? 'No excerpt'}</p>)}</article><article><h3>Explanation</h3><p>{explanation.hypothesis}</p><h3>Proposed action</h3>{explanation.recommendations.map((recommendation, index) => <p key={index}>{recommendation.action}<br /><small>{recommendation.rationale}</small></p>)}</article></div>}</section>}
      {screen === 'Incident timeline' && <section><span className="eyebrow">INCIDENT {investigation.incident_id ?? 'NOT CREATED'}</span><h2>Incident timeline</h2><article><h3>Investigation run</h3><p>{investigation.created_at} · {investigation.run_id}</p>{incident?.outcomes.map(outcome => <p key={outcome.outcome_id}><strong>{outcome.type}</strong> · {outcome.event_time}<br />{outcome.note}<br />Retention: {outcome.retention_status} {outcome.retention_status !== 'retained' && <button disabled={busy} onClick={() => retryRetention(outcome.outcome_id)}>Retry retention</button>}</p>)}{!live && <p>Load an investigation to record an outcome.</p>}</article>{live && investigation.incident_id && <article><h3>Record outcome</h3><label>Type<select value={outcomeType} onChange={event => setOutcomeType(event.target.value as 'decision' | 'measured_result')}><option value="decision">Decision</option><option value="measured_result">Measured result</option></select></label><label>Note<textarea maxLength={280} value={note} onChange={event => setNote(event.target.value)} /></label><button className="primary" disabled={busy} onClick={submitOutcome}>Save outcome</button></article>}</section>}
    </main><footer>{live ? 'Live API result' : 'Illustrative contract fixture'} · Results show association, not causation.</footer>
  </div>
}
