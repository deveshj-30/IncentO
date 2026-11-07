import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import App from './App'

describe('frontend shell', () => {
  it('renders the fixture overview with a synthetic-data label', () => {
    const html = renderToStaticMarkup(<App />)
    expect(html).toContain('Synthetic data')
    expect(html).toContain('IncentO')
    expect(html).toContain('Acquisition bonus')
    expect(html).toContain('19 points')
    expect(html).toContain('Incident timeline')
    expect(html).toContain('value="risk"')
    expect(html).toContain('value="POL-RISK-001"')
    expect(html).toContain('value="2026-11-01"')
  })
})
