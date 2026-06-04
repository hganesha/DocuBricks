import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, XCircle } from 'lucide-react'
import { Button, Input, Layout } from '../components'
import { useOnboardingStore } from '../store'
import { api } from '../api'
import type { WorkspaceValidationResult } from '../types'

export default function WorkspaceScreen() {
  const navigate = useNavigate()
  const store = useOnboardingStore()

  const [host, setHost] = useState(store.config.workspace?.host ?? '')
  const [token, setToken] = useState('')
  const [validating, setValidating] = useState(false)
  const [result, setResult] = useState<WorkspaceValidationResult | null>(
    store.config.workspace?.host
      ? { connected: true, ...store.config.workspace }
      : null
  )

  async function handleVerify() {
    setValidating(true)
    setResult(null)
    const r = await api.validateWorkspace(host, token)
    setResult(r)
    setValidating(false)
  }

  function handleContinue() {
    store.updateWorkspace({
      host,
      cloud: result!.cloud ?? 'unknown',
      region: result!.region ?? '',
      plan: result!.plan ?? '',
      ucEnabled: result!.ucEnabled ?? false,
      existingCatalog: result!.existingCatalog ?? null,
    })
    navigate('/resources')
  }

  return (
    <Layout step={3}>
      <h1 className="text-2xl font-semibold tracking-tighter text-gray-900">
        Connect your Databricks workspace.
      </h1>
      <p className="text-sm text-gray-500 mt-1">
        We'll provision DocuBricks resources inside this workspace.
      </p>

      <div className="flex flex-col gap-5 mt-8">
        <Input
          label="Workspace URL"
          value={host}
          onChange={(v) => { setHost(v); setResult(null) }}
          placeholder="https://adb-xxxx.azuredatabricks.net"
        />
        <Input
          label="Personal access token"
          type="password"
          value={token}
          onChange={(v) => { setToken(v); setResult(null) }}
          hint="How to create a token →"
        />

        <div>
          <Button
            variant="secondary"
            loading={validating}
            disabled={!host || !token || validating}
            onClick={handleVerify}
          >
            {validating ? 'Verifying...' : 'Verify connection'}
          </Button>

          {result?.connected && (
            <div className="mt-3 flex items-start gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
              <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
              <div>
                <div className="font-medium">Connected</div>
                <div className="text-xs text-green-600 mt-0.5">
                  {result.cloud?.toUpperCase()} · {result.region} · {result.plan} plan · Unity Catalog enabled
                  {result.existingCatalog && ` · Detected: ${result.existingCatalog}`}
                </div>
              </div>
            </div>
          )}

          {result && !result.connected && (
            <div className="mt-3 flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
              <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <div>{result.error}</div>
            </div>
          )}
        </div>

        <p className="text-xs text-gray-400 border-t border-gray-100 pt-4">
          Your token is used once to create a service principal, then discarded. All subsequent access uses scoped credentials.
        </p>
      </div>

      <div className="flex justify-between items-center mt-10">
        <Button variant="ghost" onClick={() => navigate('/vertical')}>
          ← Back
        </Button>
        <Button disabled={!result?.connected} onClick={handleContinue}>
          Continue →
        </Button>
      </div>
    </Layout>
  )
}
