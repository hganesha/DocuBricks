import { useNavigate } from 'react-router-dom'
import { Button, Layout } from '../components'
import { useOnboardingStore } from '../store'

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

interface RowProps {
  label: string
  value: string
}

function Row({ label, value }: RowProps) {
  return (
    <div className="flex justify-between items-baseline py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-gray-900">{value}</span>
    </div>
  )
}

export default function ReviewScreen() {
  const navigate = useNavigate()
  const { config } = useOnboardingStore()

  const proj = config.project!
  const ws = config.workspace!
  const res = config.resources!

  return (
    <Layout step={5}>
      <h1 className="text-2xl font-semibold tracking-tighter text-gray-900">
        Ready to deploy.
      </h1>
      <p className="text-sm text-gray-500 mt-1">
        Check your configuration before we provision resources.
      </p>

      {/* Config summary */}
      <div className="bg-gray-50 border border-gray-100 rounded-xl p-6 mt-8">
        <Row label="Project" value={proj.name} />
        <Row label="Environment" value={capitalize(proj.environment)} />
        <Row label="Owner" value={proj.ownerEmail} />
        <Row label="Vertical" value="Financial Services (4 document types)" />
        <Row label="Workspace" value={ws.host.replace('https://', '')} />
        <Row
          label="Catalog"
          value={`${res.catalogName} (${res.catalogMode})`}
        />
        <Row label="Compute" value="Serverless" />
        <Row
          label="Lakebase"
          value={res.lakebaseMode === 'create' ? 'New (managed)' : 'Existing'}
        />
        <Row label="Genie" value={res.genieName} />
      </div>

      {/* What will be created */}
      <div className="mt-8">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          What will be created
        </h3>

        <div className="flex flex-col gap-5">
          {/* Data infrastructure */}
          <div>
            <p className="text-xs font-medium text-gray-700 mb-1">
              Data infrastructure
            </p>
            <ul className="text-xs text-gray-500 leading-6 list-none">
              <li>5 Unity Catalog schemas (bronze · silver · gold · schema_registry · eval)</li>
              <li>4 DLT streaming tables (Bronze → Silver)</li>
              <li>4 Gold materialized views</li>
              <li>1 Vector Search index (BGE-large embeddings)</li>
            </ul>
          </div>

          {/* Document schemas */}
          <div>
            <p className="text-xs font-medium text-gray-700 mb-1">
              Document schemas
            </p>
            <ul className="text-xs text-gray-500 leading-6 list-none">
              <li>Mortgage application (URLA/MISMO-aligned, 280+ fields)</li>
              <li>KYC / CDD form (40 canonical domains, bank-grade)</li>
              <li>AML SAR (FinCEN-aligned)</li>
              <li>Invoice (AP/AR workflows)</li>
            </ul>
          </div>

          {/* Applications */}
          <div>
            <p className="text-xs font-medium text-gray-700 mb-1">
              Applications
            </p>
            <ul className="text-xs text-gray-500 leading-6 list-none">
              <li>DocuBricks Portal (upload · status · Genie chat)</li>
              <li>Review &amp; Correction UI</li>
              <li>Admin &amp; Schema Manager</li>
            </ul>
          </div>
        </div>
      </div>

      <p className="text-xs text-gray-400 mt-6">
        Estimated deploy time: 3–4 minutes
      </p>

      <div className="flex justify-between items-center mt-8">
        <Button variant="ghost" onClick={() => navigate('/resources')}>
          ← Back
        </Button>
        <Button onClick={() => navigate('/deploying')}>
          Deploy DocuBricks →
        </Button>
      </div>
    </Layout>
  )
}
