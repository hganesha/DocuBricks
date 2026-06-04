import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Layout, RadioGroup } from '../components'
import { useOnboardingStore } from '../store'
import type { CatalogMode, ComputeMode, LakebaseMode, GenieMode } from '../types'

export default function ResourcesScreen() {
  const navigate = useNavigate()
  const store = useOnboardingStore()

  const ws = store.config.workspace
  const proj = store.config.project

  const [catalogMode, setCatalogMode] = useState<CatalogMode>(
    store.config.resources?.catalogMode ?? (ws?.existingCatalog ? 'existing' : 'create')
  )
  const [catalogName, setCatalogName] = useState(
    store.config.resources?.catalogName ??
      (ws?.existingCatalog ?? `docubricks_${proj?.slug ?? 'prod'}`)
  )
  const [computeMode, setComputeMode] = useState<ComputeMode>(
    store.config.resources?.computeMode ?? 'serverless'
  )
  const [lakebaseMode, setLakebaseMode] = useState<LakebaseMode>(
    store.config.resources?.lakebaseMode ?? 'create'
  )
  const [genieMode, setGenieMode] = useState<GenieMode>(
    store.config.resources?.genieMode ?? 'create'
  )

  const genieName = `DocuBricks FS — ${proj?.name ?? ''}`

  // Keep catalogName in sync when mode changes
  function handleCatalogModeChange(v: string) {
    const mode = v as CatalogMode
    setCatalogMode(mode)
    if (mode === 'existing') {
      setCatalogName(ws?.existingCatalog ?? `docubricks_${proj?.slug ?? 'prod'}`)
    } else {
      setCatalogName(`docubricks_${proj?.slug ?? 'prod'}`)
    }
  }

  function handleContinue() {
    store.updateResources({
      catalogMode,
      catalogName,
      computeMode,
      clusterId: null,
      lakebaseMode,
      lakebaseConnStr: null,
      genieMode,
      genieSpaceId: null,
      genieName,
    })
    navigate('/review')
  }

  return (
    <Layout step={4}>
      <h1 className="text-2xl font-semibold tracking-tighter text-gray-900">
        Resources.
      </h1>
      <p className="text-sm text-gray-500 mt-1">
        We pre-fill what we detected. Change anything you need.
      </p>

      <div className="flex flex-col gap-8 mt-8">
        {/* Unity Catalog */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Unity Catalog
          </label>
          <RadioGroup
            value={catalogMode}
            onChange={handleCatalogModeChange}
            options={[
              {
                value: 'existing',
                label: 'Use existing',
                description: ws?.existingCatalog ?? 'No catalog detected',
              },
              {
                value: 'create',
                label: 'Create new',
                description: `docubricks_${proj?.slug ?? 'prod'}`,
              },
            ]}
          />
          <p className="text-xs text-gray-400 mt-2">
            Schemas (bronze, silver, gold, schema_registry, eval) will be created inside this catalog.
          </p>
        </div>

        {/* Compute */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Compute
          </label>
          <RadioGroup
            value={computeMode}
            onChange={(v) => setComputeMode(v as ComputeMode)}
            options={[
              {
                value: 'serverless',
                label: 'Serverless (recommended)',
                description: 'No cluster management. Auto-scales to zero.',
              },
              {
                value: 'existing',
                label: 'Existing cluster (advanced)',
              },
            ]}
          />
        </div>

        {/* Operational Database */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Operational Database
          </label>
          <RadioGroup
            value={lakebaseMode}
            onChange={(v) => setLakebaseMode(v as LakebaseMode)}
            options={[
              {
                value: 'create',
                label: 'Create Lakebase',
                description: 'Managed PostgreSQL. Free tier included.',
              },
              {
                value: 'existing',
                label: 'Connect existing PostgreSQL (advanced)',
              },
            ]}
          />
        </div>

        {/* Genie Workspace */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Genie Workspace
          </label>
          <RadioGroup
            value={genieMode}
            onChange={(v) => setGenieMode(v as GenieMode)}
            options={[
              {
                value: 'create',
                label: `Create "${genieName}"`,
              },
              {
                value: 'existing',
                label: 'Use existing (enter space ID)',
              },
            ]}
          />
        </div>
      </div>

      <div className="flex justify-between items-center mt-10">
        <Button variant="ghost" onClick={() => navigate('/workspace')}>
          ← Back
        </Button>
        <Button onClick={handleContinue}>Continue →</Button>
      </div>
    </Layout>
  )
}
