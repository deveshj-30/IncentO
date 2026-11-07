import { useState } from 'react'
import type { components } from './types/contracts'
import fixture from '../../contracts/examples/investigation-response.json'

type Investigation = components['schemas']['Investigation']
type Screen = 'Overview' | 'Investigation' | 'Incident timeline'

const investigation = fixture as Investigation

export default function App() {
  const [screen, setScreen] = useState<Screen>('Overview')
  const [compare, setCompare] = useState(false)
  const { analysis, explanation } = investigation

  return <div className="shell">
    <header><div><span className="eyebrow">REVENUE OPERATIONS · DEMO</span><h1>IncentiveTrap</h1></div><span className="badge">Synthetic data</span></header>
    <nav aria-label="Main navigation">{(['Overview', 'Investigation', 'Incident timeline'] as const).map(item => <button className={screen === item ? 'active' : ''} onClick={() => setScreen(item)} key={item}>{item}</button>)}</nav>
    <main>
      {screen === 'Overview' && <section><span className="eyebrow">POLICY OVERVIEW</span><h2>Acquisition bonus</h2><p>Review whether month-end deals show signs of poor customer fit.</p><div className="grid">{analysis.metrics.map(metric => <article key={metric.name}><span className="eyebrow">{metric.name.replaceAll('_', ' ')}</span><h3>{metric.gap === null ? '—' : `${Math.round(metric.gap * 100)} points`}</h3><span className="badge">{metric.status.replaceAll('_', ' ')}</span><p>{metric.month_end_n} month-end / {metric.other_n} other deals</p></article>)}</div><button className="primary" onClick={() => setScreen('Investigation')}>View investigation →</button></section>}
      {screen === 'Investigation' && <section><span className="eyebrow">RUN {investigation.run_id}</span><h2>Investigation</h2><div className="badges"><span className="badge">Memory: {explanation.memory_status}</span><span className="badge">Explanation: {explanation.explanation_source}</span><span className="badge">As of {new Date(investigation.as_of).toLocaleDateString()}</span></div><div className="tabs"><button className={!compare ? 'active' : ''} onClick={() => setCompare(false)}>Findings</button><button className={compare ? 'active' : ''} onClick={() => setCompare(true)}>Compare memory</button></div>{compare ? <article><h3>What memory contributed</h3><p>Mode: {investigation.memory_mode}. {explanation.recalled.length} recalled item(s).</p>{explanation.recalled.map(memory => <p key={memory.id}><strong>{memory.summary}</strong><br />{memory.memory_type} · {memory.event_time} · {memory.id}</p>)}{explanation.recommendations.map((recommendation, index) => <p key={index}>Recommendation {index + 1} used: {recommendation.history_influence.join(', ') || 'no memory'}</p>)}</article> : <div className="grid two"><article><h3>Evidence</h3>{analysis.evidence.map(evidence => <p key={evidence.id}><strong>{evidence.id}</strong> · {evidence.source_type}<br />{evidence.excerpt ?? 'No excerpt'}</p>)}</article><article><h3>Explanation</h3><p>{explanation.hypothesis}</p><h3>Proposed action</h3>{explanation.recommendations.map((recommendation, index) => <p key={index}>{recommendation.action}<br /><small>{recommendation.rationale}</small></p>)}</article></div>}</section>}
      {screen === 'Incident timeline' && <section><span className="eyebrow">INCIDENT {investigation.incident_id ?? 'NOT CREATED'}</span><h2>Incident timeline</h2><article><h3>Investigation run</h3><p>{investigation.created_at} · {investigation.run_id}</p><p>Outcome entry will be available when the API is connected.</p></article></section>}
    </main>
    <footer>Illustrative contract fixture · Results show association, not causation.</footer>
  </div>
}
