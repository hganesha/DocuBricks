import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Layout, VerticalCard } from '../components'
import { useOnboardingStore } from '../store'

export default function VerticalScreen() {
  const navigate = useNavigate()
  const store = useOnboardingStore()

  const [selected, setSelected] = useState(store.config.vertical ?? '')

  function handleContinue() {
    store.setVertical(selected)
    navigate('/workspace')
  }

  return (
    <Layout step={2}>
      <h1 className="text-2xl font-semibold tracking-tighter text-gray-900">
        Which industry?
      </h1>
      <p className="text-sm text-gray-500 mt-1">
        Choose the document schema library for your vertical.
      </p>

      <div className="grid grid-cols-2 gap-4 mt-8">
        <VerticalCard
          title="Financial Services"
          docTypes={['Mortgage · KYC/CDD', 'AML SAR · Invoice', 'Trade confirmation']}
          fieldCount="4 document types · 30+ schema fields"
          selected={selected === 'fs'}
          onClick={() => setSelected('fs')}
        />
        <VerticalCard
          title="Healthcare"
          docTypes={['Clinical notes · EOB', 'Lab reports · Prior auth']}
          fieldCount="5 document types"
          available="Q3 2026"
        />
        <VerticalCard
          title="Legal"
          docTypes={['NDA · Contracts', 'IP filings · Court']}
          fieldCount="4 document types"
          available="Q3 2026"
        />
        <VerticalCard
          title="Insurance"
          docTypes={['Claims · Policy', 'Underwriting · Loss run']}
          fieldCount="4 document types"
          available="Q4 2026"
        />
      </div>

      <p className="text-xs text-gray-400 mt-4">
        Need another vertical? → Join the waitlist
      </p>

      <div className="flex justify-between items-center mt-10">
        <Button variant="ghost" onClick={() => navigate('/project')}>
          ← Back
        </Button>
        <Button disabled={!selected} onClick={handleContinue}>
          Continue →
        </Button>
      </div>
    </Layout>
  )
}
