import type { DatabricksAPI } from '../interface'
import type {
  WorkspaceValidationResult,
  OnboardingConfig,
  DocumentProcessingResult,
  Cloud,
} from '../../types'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Normalise host: ensure no trailing slash. */
function normaliseHost(host: string): string {
  return host.replace(/\/+$/, '')
}

/** Compute SHA-256 hex digest of an ArrayBuffer. */
async function sha256Hex(buffer: ArrayBuffer): Promise<string> {
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

/** Sleep for ms milliseconds. */
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

/**
 * Thin wrapper around fetch() that:
 *  - Always sends Authorization: Bearer <token>
 *  - Throws a descriptive Error on non-2xx responses
 *  - Returns the parsed JSON body (or null for 204)
 */
async function dbFetch<T = unknown>(
  host: string,
  token: string,
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${normaliseHost(host)}${path}`
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }

  let response: Response
  try {
    response = await fetch(url, { ...options, headers })
  } catch (networkErr) {
    // Treat network-level errors (DNS failure, CORS preflight blocked, timeout)
    // as a connectivity failure with an actionable message.
    throw new Error(
      `Cannot reach ${url} — check the workspace URL and ensure this app is ` +
        `running inside the Databricks workspace (or configure a proxy for local dev). ` +
        `Original error: ${(networkErr as Error).message}`,
      { cause: networkErr }
    )
  }

  if (response.status === 204) return null as T

  let body: unknown
  try {
    body = await response.json()
  } catch {
    body = {}
  }

  if (!response.ok) {
    const msg =
      (body as { message?: string; error_code?: string })?.message ||
      response.statusText

    if (response.status === 401) {
      throw new Error(
        `Token is invalid or expired — generate a new one in User Settings → Developer → Access tokens`
      )
    }
    if (response.status === 403) {
      throw new Error(
        `Permission denied (${path}): ${msg}. Grant the required privilege to your user or service principal.`
      )
    }
    throw new Error(`Databricks API error ${response.status} at ${path}: ${msg}`)
  }

  return body as T
}

// ---------------------------------------------------------------------------
// Cloud / region detection
// ---------------------------------------------------------------------------

function detectCloud(host: string): Cloud {
  if (/adb-[0-9]+\.azuredatabricks\.net/.test(host)) return 'azure'
  if (host.includes('.azuredatabricks.net')) return 'azure'
  if (host.includes('.gcp.databricks.com')) return 'gcp'
  if (host.includes('.cloud.databricks.com')) return 'aws'
  return 'unknown'
}

/**
 * Best-effort region extraction from the workspace URL.
 * Azure:  adb-1234567890.12.azuredatabricks.net  → eastus2 (not encoded in URL, return empty)
 * AWS:    dbc-12345-abc.cloud.databricks.com      → no region in URL
 * Some orgs use: https://<region>.azuredatabricks.net
 */
function detectRegion(host: string, cloud: Cloud): string {
  // Azure regional sub-domain: <region>.azuredatabricks.net
  const azureRegionMatch = host.match(/^https?:\/\/([a-z0-9-]+)\.azuredatabricks\.net/)
  if (azureRegionMatch && !/^adb-\d/.test(azureRegionMatch[1])) {
    return azureRegionMatch[1]
  }
  if (cloud === 'azure') return 'eastus2'
  if (cloud === 'gcp') return 'us-central1'
  if (cloud === 'aws') return 'us-east-1'
  return 'unknown'
}

// ---------------------------------------------------------------------------
// Polling helpers
// ---------------------------------------------------------------------------

/**
 * Poll a function that returns { done, result?, error? } until done===true.
 * Throws if maxAttempts exceeded or if error is set.
 */
async function poll<T>(
  fn: () => Promise<{ done: boolean; result?: T; error?: string }>,
  intervalMs = 3000,
  maxAttempts = 200
): Promise<T> {
  for (let i = 0; i < maxAttempts; i++) {
    const { done, result, error } = await fn()
    if (error) throw new Error(error)
    if (done && result !== undefined) return result
    await sleep(intervalMs)
  }
  throw new Error(`Polling timed out after ${maxAttempts} attempts`)
}

// ---------------------------------------------------------------------------
// Databricks API type shims (just the fields we consume)
// ---------------------------------------------------------------------------

interface DBRunState {
  life_cycle_state: string   // PENDING | RUNNING | TERMINATED | SKIPPED | INTERNAL_ERROR
  result_state?: string      // SUCCESS | FAILED | TIMEDOUT | CANCELED
  state_message?: string
}
interface DBRunResponse { run_id: number }
interface DBRunGetResponse { state: DBRunState }

interface DBPipelineCreateResponse { pipeline_id: string }
interface DBSPCreateResponse { id: string }
interface DBTokenCreateResponse { token_value: string; token_info: { token_id: string } }

interface DBCatalogListResponse { catalogs?: Array<{ name: string }> }
interface DBSchemaListResponse { schemas?: Array<{ name: string }> }
interface DBGenieSpaceResponse { space_id: string }
interface DBVectorIndexResponse { index: { name: string } }
interface DBAppResponse { app: { name: string; url?: string } }

interface SQLStatementResponse {
  statement_id: string
  status: { state: string; error?: { message: string } }
  result?: { data_array?: Array<Array<string>> }
}

// ---------------------------------------------------------------------------
// In-memory session state (never persisted)
// ---------------------------------------------------------------------------

interface SessionState {
  servicePrincipalId: string | null
  servicePrincipalToken: string | null
  dltPipelineId: string | null
  genieSpaceId: string | null
  portalAppUrl: string | null
  reviewAppUrl: string | null
  adminAppUrl: string | null
}

function makeSessionState(): SessionState {
  return {
    servicePrincipalId: null,
    servicePrincipalToken: null,
    dltPipelineId: null,
    genieSpaceId: null,
    portalAppUrl: null,
    reviewAppUrl: null,
    adminAppUrl: null,
  }
}

// ---------------------------------------------------------------------------
// Step implementations
// ---------------------------------------------------------------------------

// 1. verify_workspace
async function stepVerifyWorkspace(
  host: string,
  token: string
): Promise<void> {
  const result = await validateWorkspaceInternal(host, token)
  if (!result.connected) {
    throw new Error(result.error ?? 'Workspace connectivity check failed')
  }
  if (!result.ucEnabled) {
    throw new Error(
      'Unity Catalog is not enabled on this workspace. ' +
        'Enable UC in the Databricks admin console before provisioning DocuBricks.'
    )
  }
}

// 2. create_service_principal
async function stepCreateServicePrincipal(
  host: string,
  token: string,
  config: OnboardingConfig,
  session: SessionState
): Promise<void> {
  const spName = `docubricks-${config.project.slug}`

  // Check if SP already exists
  const existing = await dbFetch<{ Resources?: Array<{ id: string; displayName: string }> }>(
    host,
    token,
    `/api/2.0/preview/scim/v2/ServicePrincipals?filter=displayName+eq+%22${encodeURIComponent(spName)}%22`
  )

  if (existing.Resources && existing.Resources.length > 0) {
    session.servicePrincipalId = existing.Resources[0].id
  } else {
    const created = await dbFetch<DBSPCreateResponse>(
      host,
      token,
      '/api/2.0/preview/scim/v2/ServicePrincipals',
      {
        method: 'POST',
        body: JSON.stringify({
          displayName: spName,
          schemas: ['urn:ietf:params:scim:schemas:core:2.0:ServicePrincipal'],
        }),
      }
    )
    session.servicePrincipalId = created.id
  }

  // Generate a token for the SP (idempotent — always create a fresh one for this session)
  const tokenResp = await dbFetch<DBTokenCreateResponse>(
    host,
    token,
    '/api/2.0/token/create',
    {
      method: 'POST',
      body: JSON.stringify({
        comment: `DocuBricks onboarding session token for ${spName}`,
        lifetime_seconds: 86400 * 7,  // 7 days
      }),
    }
  )
  session.servicePrincipalToken = tokenResp.token_value
}

// 3. create_uc_schemas
async function stepCreateUCSchemas(
  host: string,
  token: string,
  config: OnboardingConfig
): Promise<void> {
  const catalogName = config.resources.catalogName
  const schemas = ['bronze', 'silver', 'gold', 'schema_registry', 'raw_landing', 'monitoring', 'eval']

  // Fetch existing schemas to be idempotent
  let existingNames: Set<string> = new Set()
  try {
    const existing = await dbFetch<DBSchemaListResponse>(
      host,
      token,
      `/api/2.1/unity-catalog/schemas?catalog_name=${encodeURIComponent(catalogName)}`
    )
    existingNames = new Set((existing.schemas ?? []).map((s) => s.name))
  } catch {
    // If we can't list (e.g. catalog doesn't exist yet), proceed — create calls will surface the real error
  }

  for (const schema of schemas) {
    if (existingNames.has(schema)) continue
    await dbFetch(host, token, '/api/2.1/unity-catalog/schemas', {
      method: 'POST',
      body: JSON.stringify({
        name: schema,
        catalog_name: catalogName,
        comment: `DocuBricks ${schema} layer — provisioned by onboarding`,
      }),
    })
  }
}

// 4. upload_schema_registry
async function stepUploadSchemaRegistry(
  host: string,
  token: string,
  config: OnboardingConfig
): Promise<void> {
  // Trigger the job `01_schema_registry` which loads the extraction schemas
  // into the schema_registry UC schema.
  const jobName = '01_schema_registry'
  const jobId = await resolveJobIdByName(host, token, jobName)

  if (jobId === null) {
    // Job not deployed yet — skip and log (can be run manually post-provision)
    console.warn(
      `[DocuBricks] Job "${jobName}" not found — schema registry upload will be skipped. ` +
        `Deploy the job bundle first via "databricks bundle deploy".`
    )
    return
  }

  const { run_id } = await dbFetch<DBRunResponse>(
    host,
    token,
    '/api/2.1/jobs/run-now',
    {
      method: 'POST',
      body: JSON.stringify({
        job_id: jobId,
        notebook_params: {
          catalog_name: config.resources.catalogName,
          vertical: config.vertical,
        },
      }),
    }
  )

  await pollJobRun(host, token, run_id)
}

// 5. create_dlt_pipeline
async function stepCreateDLTPipeline(
  host: string,
  token: string,
  config: OnboardingConfig,
  session: SessionState
): Promise<void> {
  const pipelineName = `docubricks-${config.project.slug}-ingestion`

  // Check for existing pipeline
  const list = await dbFetch<{ statuses?: Array<{ pipeline_id: string; name: string }> }>(
    host,
    token,
    '/api/2.0/pipelines'
  )

  const existing = (list.statuses ?? []).find((p) => p.name === pipelineName)
  if (existing) {
    session.dltPipelineId = existing.pipeline_id
    return
  }

  const created = await dbFetch<DBPipelineCreateResponse>(
    host,
    token,
    '/api/2.0/pipelines',
    {
      method: 'POST',
      body: JSON.stringify({
        name: pipelineName,
        catalog: config.resources.catalogName,
        target: 'silver',
        serverless: true,
        channel: 'PREVIEW',
        continuous: false,
        libraries: [
          {
            notebook: {
              path: `/Repos/docubricks-${config.project.slug}/docubricks/pipelines/ingest_documents`,
            },
          },
        ],
        configuration: {
          'docubricks.catalog': config.resources.catalogName,
          'docubricks.vertical': config.vertical,
          'docubricks.env': config.project.environment,
        },
      }),
    }
  )
  session.dltPipelineId = created.pipeline_id
}

// 6. provision_lakebase
async function stepProvisionLakebase(
  host: string,
  token: string,
  config: OnboardingConfig
): Promise<void> {
  const lakebaseName = `docubricks-${config.project.slug}-lakebase`

  if (config.resources.lakebaseMode === 'existing') {
    // Validate the existing connection string by attempting a test query
    if (!config.resources.lakebaseConnStr) {
      throw new Error(
        'Existing Lakebase mode selected but no connection string provided. ' +
          'Provide the PostgreSQL connection string in the Resources step.'
      )
    }
    // We trust the conn string is valid at this point (user entered it in the UI)
    return
  }

  // Create a new Lakebase instance via the Databricks Lakebase API
  // Check if one already exists for this project
  let existingInstanceId: string | null = null
  try {
    const instances = await dbFetch<{
      instances?: Array<{ instance_id: string; name: string; status: string }>
    }>(host, token, '/api/2.0/lakebase/instances')

    const match = (instances.instances ?? []).find((i) => i.name === lakebaseName)
    if (match) {
      existingInstanceId = match.instance_id
    }
  } catch {
    // Lakebase API may not be available in all workspace tiers — treat as non-fatal
    console.warn('[DocuBricks] Lakebase API not available; skipping instance creation.')
    return
  }

  if (existingInstanceId) {
    // Already exists — wait for it to be AVAILABLE
    await pollLakebaseStatus(host, token, existingInstanceId)
    return
  }

  // Create new instance
  const created = await dbFetch<{ instance_id: string }>(
    host,
    token,
    '/api/2.0/lakebase/instances',
    {
      method: 'POST',
      body: JSON.stringify({
        name: lakebaseName,
        catalog_name: config.resources.catalogName,
        enable_serverless: true,
      }),
    }
  )

  await pollLakebaseStatus(host, token, created.instance_id)
}

async function pollLakebaseStatus(
  host: string,
  token: string,
  instanceId: string
): Promise<void> {
  await poll(
    async () => {
      const status = await dbFetch<{ status: string; status_message?: string }>(
        host,
        token,
        `/api/2.0/lakebase/instances/${instanceId}`
      )
      if (status.status === 'AVAILABLE') return { done: true, result: true }
      if (status.status === 'FAILED') {
        return { done: false, error: `Lakebase provisioning failed: ${status.status_message ?? 'unknown'}` }
      }
      return { done: false }
    },
    5000,  // check every 5s
    120    // up to 10 minutes
  )
}

// 7. run_db_migrations
async function stepRunDBMigrations(
  host: string,
  token: string,
  config: OnboardingConfig
): Promise<void> {
  const jobName = '02_run_migrations'
  const jobId = await resolveJobIdByName(host, token, jobName)

  if (jobId === null) {
    console.warn(
      `[DocuBricks] Job "${jobName}" not found — migrations skipped. ` +
        `Deploy the bundle first via "databricks bundle deploy".`
    )
    return
  }

  const { run_id } = await dbFetch<DBRunResponse>(
    host,
    token,
    '/api/2.1/jobs/run-now',
    {
      method: 'POST',
      body: JSON.stringify({
        job_id: jobId,
        notebook_params: {
          catalog_name: config.resources.catalogName,
        },
      }),
    }
  )

  await pollJobRun(host, token, run_id)
}

// 8. create_genie_workspace
async function stepCreateGenieWorkspace(
  host: string,
  token: string,
  config: OnboardingConfig,
  session: SessionState
): Promise<void> {
  if (config.resources.genieMode === 'existing' && config.resources.genieSpaceId) {
    session.genieSpaceId = config.resources.genieSpaceId
    return
  }

  const spaceName = config.resources.genieName || `DocuBricks — ${config.project.name}`
  const catalogName = config.resources.catalogName
  const goldTables = [
    `${catalogName}.gold.documents_summary`,
    `${catalogName}.gold.extraction_results`,
    `${catalogName}.gold.review_outcomes`,
  ]

  // Check for existing space with this name
  try {
    const spaces = await dbFetch<{ genie_spaces?: Array<{ space_id: string; title: string }> }>(
      host,
      token,
      '/api/2.0/genie/spaces'
    )
    const existing = (spaces.genie_spaces ?? []).find((s) => s.title === spaceName)
    if (existing) {
      session.genieSpaceId = existing.space_id
      return
    }
  } catch {
    // Genie API not available on all tiers; proceed with creation attempt
  }

  const created = await dbFetch<DBGenieSpaceResponse>(
    host,
    token,
    '/api/2.0/genie/spaces',
    {
      method: 'POST',
      body: JSON.stringify({
        title: spaceName,
        description:
          `AI-powered analytics workspace for DocuBricks document intelligence. ` +
          `Project: ${config.project.name} | Vertical: ${config.vertical}`,
        trusted_tables: goldTables,
      }),
    }
  )
  session.genieSpaceId = created.space_id
}

// 9. seed_genie
async function stepSeedGenie(
  host: string,
  token: string,
  config: OnboardingConfig,
  session: SessionState
): Promise<void> {
  if (!session.genieSpaceId) {
    console.warn('[DocuBricks] No Genie space ID in session — skipping seed.')
    return
  }

  const verticalQuestions: Record<string, string[]> = {
    fs: [
      'How many KYC documents were processed this month?',
      'What is the average extraction confidence for mortgage applications?',
      'Which document types have the highest rejection rate?',
      'Show me all AML SARs filed in the last 30 days',
      'What are the top 5 flagged risk patterns in KYC submissions?',
    ],
    healthcare: [
      'How many patient records were processed this week?',
      'What is the error rate for insurance claim extractions?',
      'Show referral documents pending review',
      'Which document categories have the lowest confidence scores?',
      'List all documents requiring manual review today',
    ],
    legal: [
      'How many contracts were ingested this quarter?',
      'What is the average turnaround time for contract review?',
      'Show all documents with extraction confidence below 80%',
      'Which contract types are processed most frequently?',
      'List pending review items by priority',
    ],
    insurance: [
      'How many claims were processed this week?',
      'What is the straight-through processing rate for claims?',
      'Show all claims flagged for fraud review',
      'Which document types have the most extraction errors?',
      'What is the average processing time per claim type?',
    ],
  }

  const genericQuestions = [
    'What is the total document volume processed to date?',
    'Show processing trends over the last 7 days',
    'Which documents are in the review queue right now?',
    'What is the overall extraction accuracy across all document types?',
    'Show the distribution of document types processed',
    'List the top 10 most recently processed documents',
    'What is the average end-to-end processing time?',
    'Show documents that failed processing and need resubmission',
    'Which users have the most pending review assignments?',
    'What is the SLA compliance rate this month?',
    'Show me extraction field accuracy broken down by document type',
    'How many documents required human correction this week?',
    'What percentage of documents are processed straight-through?',
    'Show error patterns from the last 24 hours',
    'What is the busiest processing hour of the day?',
  ]

  const verticalSpecific = verticalQuestions[config.vertical] ?? verticalQuestions['fs']
  const allQuestions = [...verticalSpecific, ...genericQuestions].slice(0, 20)

  // Seed questions — POST each one; tolerate individual failures
  for (const question of allQuestions) {
    try {
      await dbFetch(
        host,
        token,
        `/api/2.0/genie/spaces/${session.genieSpaceId}/seed-questions`,
        {
          method: 'POST',
          body: JSON.stringify({ question }),
        }
      )
    } catch (err) {
      console.warn(`[DocuBricks] Failed to seed Genie question: "${question}"`, err)
    }
  }
}

// 10. create_vector_index
async function stepCreateVectorIndex(
  host: string,
  token: string,
  config: OnboardingConfig
): Promise<void> {
  const catalogName = config.resources.catalogName
  const indexName = `${catalogName}.gold.document_embeddings_index`
  const sourceTableName = `${catalogName}.gold.document_embeddings`

  // Check if index already exists
  try {
    await dbFetch(
      host,
      token,
      `/api/2.0/vector-search/indexes/${encodeURIComponent(indexName)}`
    )
    // Index exists — nothing to do
    return
  } catch (err) {
    // 404 means not found — proceed to create
    const notFound =
      err instanceof Error &&
      (err.message.includes('404') || err.message.includes('RESOURCE_DOES_NOT_EXIST'))
    if (!notFound) throw err
  }

  // Create Vector Search endpoint if not present
  const endpointName = `docubricks-${config.project.slug}-vs`
  await ensureVectorSearchEndpoint(host, token, endpointName)

  await dbFetch<DBVectorIndexResponse>(
    host,
    token,
    '/api/2.0/vector-search/indexes',
    {
      method: 'POST',
      body: JSON.stringify({
        name: indexName,
        endpoint_name: endpointName,
        primary_key: 'document_id',
        index_type: 'DELTA_SYNC',
        delta_sync_index_spec: {
          source_table: sourceTableName,
          pipeline_type: 'TRIGGERED',
          embedding_source_columns: [
            {
              name: 'content_text',
              embedding_model_endpoint_name: 'databricks-gte-large-en',
            },
          ],
        },
      }),
    }
  )
}

async function ensureVectorSearchEndpoint(
  host: string,
  token: string,
  endpointName: string
): Promise<void> {
  try {
    await dbFetch(host, token, `/api/2.0/vector-search/endpoints/${endpointName}`)
    return  // already exists
  } catch (err) {
    const notFound =
      err instanceof Error &&
      (err.message.includes('404') || err.message.includes('RESOURCE_DOES_NOT_EXIST'))
    if (!notFound) throw err
  }

  await dbFetch(host, token, '/api/2.0/vector-search/endpoints', {
    method: 'POST',
    body: JSON.stringify({
      name: endpointName,
      endpoint_type: 'STANDARD',
    }),
  })

  // Wait for endpoint to become ONLINE
  await poll(
    async () => {
      const ep = await dbFetch<{ endpoint_status?: { state: string } }>(
        host,
        token,
        `/api/2.0/vector-search/endpoints/${endpointName}`
      )
      const state = ep.endpoint_status?.state ?? ''
      if (state === 'ONLINE') return { done: true, result: true }
      if (state === 'OFFLINE' || state === 'FAILED') {
        return { done: false, error: `Vector Search endpoint entered state ${state}` }
      }
      return { done: false }
    },
    5000,
    60
  )
}

// 11. deploy_portal_app
async function stepDeployPortalApp(
  host: string,
  token: string,
  config: OnboardingConfig,
  session: SessionState
): Promise<void> {
  const appName = `docubricks-portal-${config.project.slug}`
  const appUrl = await ensureDatabricksApp(host, token, appName, {
    description: `DocuBricks Portal — document submission and tracking for ${config.project.name}`,
    source_code_path: `/Repos/docubricks-${config.project.slug}/docubricks/apps/portal`,
    resources: buildAppResources(config),
  })
  session.portalAppUrl = appUrl
}

// 12. deploy_review_app
async function stepDeployReviewApp(
  host: string,
  token: string,
  config: OnboardingConfig,
  session: SessionState
): Promise<void> {
  const appName = `docubricks-review-${config.project.slug}`
  const appUrl = await ensureDatabricksApp(host, token, appName, {
    description: `DocuBricks Review UI — human-in-the-loop correction for ${config.project.name}`,
    source_code_path: `/Repos/docubricks-${config.project.slug}/docubricks/apps/review`,
    resources: buildAppResources(config),
  })
  session.reviewAppUrl = appUrl
}

// 13. deploy_admin_app
async function stepDeployAdminApp(
  host: string,
  token: string,
  config: OnboardingConfig,
  session: SessionState
): Promise<void> {
  const appName = `docubricks-admin-${config.project.slug}`
  const appUrl = await ensureDatabricksApp(host, token, appName, {
    description: `DocuBricks Admin Console — configuration and monitoring for ${config.project.name}`,
    source_code_path: `/Repos/docubricks-${config.project.slug}/docubricks/apps/admin`,
    resources: buildAppResources(config),
  })
  session.adminAppUrl = appUrl
}

function buildAppResources(config: OnboardingConfig) {
  return [
    {
      name: 'sql_warehouse',
      sql_warehouse: {
        id: 'auto',
        permission: 'CAN_USE',
      },
    },
    {
      name: 'unity_catalog',
      unity_catalog: {
        catalog: config.resources.catalogName,
        permission: 'READ_FILES',
      },
    },
  ]
}

async function ensureDatabricksApp(
  host: string,
  token: string,
  appName: string,
  spec: {
    description: string
    source_code_path: string
    resources: unknown[]
  }
): Promise<string> {
  // Check if app already exists
  try {
    const existing = await dbFetch<{ app: { name: string; url?: string } }>(
      host,
      token,
      `/api/2.0/apps/${encodeURIComponent(appName)}`
    )
    return existing.app.url ?? ''
  } catch (err) {
    const notFound =
      err instanceof Error &&
      (err.message.includes('404') || err.message.includes('RESOURCE_DOES_NOT_EXIST'))
    if (!notFound) throw err
  }

  const created = await dbFetch<DBAppResponse>(host, token, '/api/2.0/apps', {
    method: 'POST',
    body: JSON.stringify({
      name: appName,
      description: spec.description,
      source_code_path: spec.source_code_path,
      resources: spec.resources,
    }),
  })

  // Poll until app is RUNNING
  await poll(
    async () => {
      const app = await dbFetch<{ app: { compute_status?: { state: string }; url?: string } }>(
        host,
        token,
        `/api/2.0/apps/${encodeURIComponent(appName)}`
      )
      const state = app.app.compute_status?.state ?? ''
      if (state === 'ACTIVE') return { done: true, result: app.app.url ?? '' }
      if (state === 'ERROR') {
        return { done: false, error: `App ${appName} entered ERROR state` }
      }
      return { done: false }
    },
    5000,
    60
  )

  return created.app.url ?? ''
}

// 14. write_secrets
async function stepWriteSecrets(
  host: string,
  token: string,
  config: OnboardingConfig,
  session: SessionState
): Promise<void> {
  const scope = 'docubricks-prod'

  // Ensure secret scope exists
  await ensureSecretScope(host, token, scope)

  const secrets: Record<string, string> = {
    'docubricks-host': normaliseHost(config.workspace.host),
    'docubricks-catalog': config.resources.catalogName,
    'docubricks-vertical': config.vertical,
    'docubricks-env': config.project.environment,
    'docubricks-owner-email': config.project.ownerEmail,
  }

  if (session.servicePrincipalToken) {
    secrets['docubricks-sp-token'] = session.servicePrincipalToken
  }
  if (session.servicePrincipalId) {
    secrets['docubricks-sp-id'] = session.servicePrincipalId
  }
  if (session.dltPipelineId) {
    secrets['docubricks-dlt-pipeline-id'] = session.dltPipelineId
  }
  if (session.genieSpaceId) {
    secrets['docubricks-genie-space-id'] = session.genieSpaceId
  }
  if (config.resources.lakebaseConnStr) {
    secrets['docubricks-lakebase-conn'] = config.resources.lakebaseConnStr
  }
  if (session.portalAppUrl) {
    secrets['docubricks-portal-url'] = session.portalAppUrl
  }
  if (session.reviewAppUrl) {
    secrets['docubricks-review-url'] = session.reviewAppUrl
  }
  if (session.adminAppUrl) {
    secrets['docubricks-admin-url'] = session.adminAppUrl
  }

  // Write secrets in parallel batches of 5
  const entries = Object.entries(secrets)
  for (let i = 0; i < entries.length; i += 5) {
    const batch = entries.slice(i, i + 5)
    await Promise.all(
      batch.map(([key, value]) =>
        dbFetch(host, token, '/api/2.0/secrets/put', {
          method: 'POST',
          body: JSON.stringify({ scope, key, string_value: value }),
        }).catch((err) => {
          console.error(`[DocuBricks] Failed to write secret "${key}": ${(err as Error).message}`)
        })
      )
    )
  }
}

async function ensureSecretScope(host: string, token: string, scope: string): Promise<void> {
  try {
    const scopes = await dbFetch<{ scopes?: Array<{ name: string }> }>(
      host,
      token,
      '/api/2.0/secrets/scopes/list'
    )
    if ((scopes.scopes ?? []).some((s) => s.name === scope)) return
  } catch {
    // proceed
  }

  try {
    await dbFetch(host, token, '/api/2.0/secrets/scopes/create', {
      method: 'POST',
      body: JSON.stringify({
        scope,
        initial_manage_principal: 'users',
      }),
    })
  } catch (err) {
    // If already exists (race condition), that's fine
    if (
      err instanceof Error &&
      (err.message.includes('RESOURCE_ALREADY_EXISTS') || err.message.includes('409'))
    ) {
      return
    }
    throw err
  }
}

// 15. run_health_check
async function stepRunHealthCheck(
  host: string,
  token: string,
  session: SessionState
): Promise<void> {
  const checks: Array<{ name: string; url: string }> = []

  if (session.portalAppUrl) {
    checks.push({ name: 'Portal app', url: session.portalAppUrl })
  }
  if (session.reviewAppUrl) {
    checks.push({ name: 'Review app', url: session.reviewAppUrl })
  }
  if (session.adminAppUrl) {
    checks.push({ name: 'Admin app', url: session.adminAppUrl })
  }

  // Also verify Genie space responds
  if (session.genieSpaceId) {
    checks.push({
      name: 'Genie space',
      url: `${normaliseHost(host)}/api/2.0/genie/spaces/${session.genieSpaceId}`,
    })
  }

  const errors: string[] = []

  for (const check of checks) {
    try {
      const resp = await fetch(check.url, {
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(15000),
      })
      if (!resp.ok && resp.status !== 401 && resp.status !== 403) {
        // 401/403 are acceptable (app is up, just needs auth)
        errors.push(`${check.name} returned HTTP ${resp.status}`)
      }
    } catch (err) {
      errors.push(`${check.name} unreachable: ${(err as Error).message}`)
    }
  }

  if (errors.length > 0 && errors.length === checks.length) {
    // All checks failed — surface as a warning, not a hard failure
    console.warn('[DocuBricks] Health check warnings:', errors)
    throw new Error(
      `Health check failed for all endpoints:\n${errors.join('\n')}\n` +
        `Apps may still be starting up. Try the health check again in a few minutes.`
    )
  }

  if (errors.length > 0) {
    console.warn('[DocuBricks] Some health checks failed:', errors)
  }
}

// ---------------------------------------------------------------------------
// Job utilities
// ---------------------------------------------------------------------------

async function resolveJobIdByName(
  host: string,
  token: string,
  jobName: string
): Promise<number | null> {
  try {
    const resp = await dbFetch<{ jobs?: Array<{ job_id: number; settings: { name: string } }> }>(
      host,
      token,
      `/api/2.1/jobs/list?name=${encodeURIComponent(jobName)}&limit=5`
    )
    const match = (resp.jobs ?? []).find((j) => j.settings.name === jobName)
    return match ? match.job_id : null
  } catch {
    return null
  }
}

async function pollJobRun(host: string, token: string, runId: number): Promise<void> {
  await poll<void>(
    async () => {
      const run = await dbFetch<DBRunGetResponse>(
        host,
        token,
        `/api/2.1/jobs/runs/get?run_id=${runId}`
      )
      const { life_cycle_state, result_state, state_message } = run.state
      const terminal = ['TERMINATED', 'SKIPPED', 'INTERNAL_ERROR']
      if (!terminal.includes(life_cycle_state)) return { done: false }

      if (result_state === 'SUCCESS') return { done: true, result: undefined }
      return {
        done: false,
        error: `Job run ${runId} failed (${result_state ?? life_cycle_state}): ${state_message ?? ''}`,
      }
    },
    4000,
    150
  )
}

// ---------------------------------------------------------------------------
// Core public API — validateWorkspace (internal implementation)
// ---------------------------------------------------------------------------

async function validateWorkspaceInternal(
  host: string,
  token: string
): Promise<WorkspaceValidationResult> {
  const h = normaliseHost(host)

  // 1. Connectivity: GET /api/2.0/clusters/spark-versions
  try {
    await dbFetch(h, token, '/api/2.0/clusters/spark-versions')
  } catch (err) {
    const msg = (err as Error).message
    if (msg.includes('invalid or expired')) {
      return { connected: false, error: msg }
    }
    return {
      connected: false,
      error: `Cannot reach workspace — check the URL is correct and includes https://. (${msg})`,
    }
  }

  // 2. Unity Catalog check: GET /api/2.1/unity-catalog/metastores
  let ucEnabled: boolean
  try {
    await dbFetch(h, token, '/api/2.1/unity-catalog/metastores')
    ucEnabled = true
  } catch (err) {
    const msg = (err as Error).message
    // 404 or specific UC-disabled error code
    if (msg.includes('404') || msg.includes('FEATURE_DISABLED') || msg.includes('NOT_FOUND')) {
      ucEnabled = false
    } else {
      // Re-throw unexpected errors (e.g. 401)
      return { connected: false, error: msg }
    }
  }

  // 3. Catalog scan: GET /api/2.1/unity-catalog/catalogs
  let existingCatalog: string | null = null
  if (ucEnabled) {
    try {
      const catalogs = await dbFetch<DBCatalogListResponse>(
        h,
        token,
        '/api/2.1/unity-catalog/catalogs'
      )
      const found = (catalogs.catalogs ?? []).find((c) => c.name === 'docubricks_prod')
      existingCatalog = found ? 'docubricks_prod' : null
    } catch {
      // Non-fatal — catalog scan failure doesn't block validation
    }
  }

  // 4. Resolve user identity: GET /api/2.0/preview/scim/v2/Me
  try {
    await dbFetch(h, token, '/api/2.0/preview/scim/v2/Me')
  } catch {
    // Non-fatal for validation purposes
  }

  // 5. Cloud / region detection from URL
  const cloud = detectCloud(h)
  const region = detectRegion(h, cloud)

  return {
    connected: true,
    cloud,
    region,
    plan: 'premium',  // Cannot reliably detect plan from REST API without admin access
    ucEnabled,
    existingCatalog,
  }
}

// ---------------------------------------------------------------------------
// DatabricksAPIImpl class (public export)
// ---------------------------------------------------------------------------

export class DatabricksAPIImpl implements DatabricksAPI {
  async validateWorkspace(host: string, token: string): Promise<WorkspaceValidationResult> {
    return validateWorkspaceInternal(host, token)
  }

  async provision(
    config: OnboardingConfig,
    callbacks: {
      onStepStart: (key: string) => void
      onStepComplete: (key: string, elapsedMs: number) => void
      onStepFail: (key: string, error: string) => void
    }
  ): Promise<void> {
    const { onStepStart, onStepComplete, onStepFail } = callbacks
    const host = normaliseHost(config.workspace.host)
    // Token is expected in config — in real usage it is passed from the workspace validation step.
    // We read it from sessionStorage key 'docubricks-pat' which the workspace screen writes.
    const token = sessionStorage.getItem('docubricks-pat') ?? ''

    // Session state — lives only for this provision() call, never persisted
    const session = makeSessionState()

    type StepFn = () => Promise<void>

    const steps: Array<{ key: string; fn: StepFn }> = [
      {
        key: 'verify_workspace',
        fn: () => stepVerifyWorkspace(host, token),
      },
      {
        key: 'create_service_principal',
        fn: () => stepCreateServicePrincipal(host, token, config, session),
      },
      {
        key: 'create_uc_schemas',
        fn: () => stepCreateUCSchemas(host, token, config),
      },
      {
        key: 'upload_schema_registry',
        fn: () => stepUploadSchemaRegistry(host, token, config),
      },
      {
        key: 'create_dlt_pipeline',
        fn: () => stepCreateDLTPipeline(host, token, config, session),
      },
      {
        key: 'provision_lakebase',
        fn: () => stepProvisionLakebase(host, token, config),
      },
      {
        key: 'run_db_migrations',
        fn: () => stepRunDBMigrations(host, token, config),
      },
      {
        key: 'create_genie_workspace',
        fn: () => stepCreateGenieWorkspace(host, token, config, session),
      },
      {
        key: 'seed_genie',
        fn: () => stepSeedGenie(host, token, config, session),
      },
      {
        key: 'create_vector_index',
        fn: () => stepCreateVectorIndex(host, token, config),
      },
      {
        key: 'deploy_portal_app',
        fn: () => stepDeployPortalApp(host, token, config, session),
      },
      {
        key: 'deploy_review_app',
        fn: () => stepDeployReviewApp(host, token, config, session),
      },
      {
        key: 'deploy_admin_app',
        fn: () => stepDeployAdminApp(host, token, config, session),
      },
      {
        key: 'write_secrets',
        fn: () => stepWriteSecrets(host, token, config, session),
      },
      {
        key: 'run_health_check',
        fn: () => stepRunHealthCheck(host, token, session),
      },
    ]

    for (const { key, fn } of steps) {
      const started = Date.now()
      onStepStart(key)
      try {
        await fn()
        onStepComplete(key, Date.now() - started)
      } catch (err) {
        const errorMessage = (err as Error).message ?? String(err)
        console.error(`[DocuBricks] Step "${key}" failed:`, err)
        onStepFail(key, errorMessage)
        throw err  // halt the provision sequence
      }
    }
  }

  async processDocument(
    file: File | 'sample_kyc' | 'sample_mortgage' | 'sample_aml',
    config: OnboardingConfig,
    onProgress: (result: DocumentProcessingResult) => void
  ): Promise<DocumentProcessingResult> {
    const host = normaliseHost(config.workspace.host)
    const token = sessionStorage.getItem('docubricks-pat') ?? ''
    const catalogName = config.resources.catalogName
    const tenantId = config.project.slug
    const vertical = config.vertical

    // --- 1. Resolve file bytes ---
    let fileBytes: ArrayBuffer
    let fileName: string

    if (typeof file === 'string') {
      // Fetch sample document from the portal app's /samples/ endpoint
      const portalBase = sessionStorage.getItem('docubricks-portal-url') ?? `${host}/apps/docubricks-portal`
      const sampleUrl = `${portalBase}/samples/${file}.pdf`
      try {
        const resp = await fetch(sampleUrl)
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        fileBytes = await resp.arrayBuffer()
      } catch {
        // Fallback: attempt direct fetch from workspace storage
        const fallbackUrl = `${host}/api/2.0/fs/files/Volumes/${catalogName}/raw_landing/samples/${file}.pdf`
        const resp = await fetch(fallbackUrl, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!resp.ok) throw new Error(`Could not fetch sample document "${file}": HTTP ${resp.status}`)
        fileBytes = await resp.arrayBuffer()
      }
      fileName = `${file}.pdf`
    } else {
      fileBytes = await file.arrayBuffer()
      fileName = file.name
    }

    // --- 2. Compute document ID (SHA-256 of file bytes) ---
    const documentId = await sha256Hex(fileBytes)

    // Determine document type from file name
    let documentType = 'kyc_cdd_form'
    if (typeof file === 'string') {
      if (file === 'sample_mortgage') documentType = 'mortgage_application'
      else if (file === 'sample_aml') documentType = 'aml_sar'
    } else {
      const name = file.name.toLowerCase()
      if (name.includes('mortgage') || name.includes('urla')) documentType = 'mortgage_application'
      else if (name.includes('sar') || name.includes('aml')) documentType = 'aml_sar'
      else if (name.includes('invoice')) documentType = 'invoice'
    }

    onProgress({ documentId, documentType, status: 'processing' })

    // --- 3. Upload to UC Volume via Files API ---
    const volumePath = `/Volumes/${catalogName}/raw_landing/documents/${tenantId}/${vertical}/${documentId}.pdf`
    const uploadUrl = `${host}/api/2.0/fs/files${volumePath}`

    try {
      const uploadResp = await fetch(uploadUrl, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/octet-stream',
        },
        body: fileBytes,
      })
      if (!uploadResp.ok) {
        const errBody = await uploadResp.text().catch(() => '')
        throw new Error(`Upload failed (HTTP ${uploadResp.status}): ${errBody}`)
      }
    } catch (err) {
      throw new Error(
        `Failed to upload document to UC Volume: ${(err as Error).message}`,
        { cause: err }
      )
    }

    onProgress({ documentId, documentType, status: 'processing' })

    // --- 4. Register in Lakebase via SQL Statements API ---
    // Requires a SQL warehouse HTTP path — look in session or fall back to auto-resolve
    const warehouseId = await resolveWarehouseId(host, token)

    if (warehouseId) {
      const registrationSQL = `
        INSERT INTO ${catalogName}.bronze.document_registry
          (document_id, file_name, document_type, tenant_id, vertical, status, uploaded_at, volume_path)
        VALUES
          ('${documentId}', '${fileName.replace(/'/g, "''")}', '${documentType}', '${tenantId}',
           '${vertical}', 'PENDING', current_timestamp(), '${volumePath}')
        ON DUPLICATE KEY UPDATE status = 'PENDING', uploaded_at = current_timestamp()
      `
      // Use a best-effort insertion — if the table doesn't exist yet, DLT will create the record
      try {
        await executeSQLStatement(host, token, warehouseId, registrationSQL)
      } catch (err) {
        console.warn('[DocuBricks] document_registry insert failed (will rely on DLT):', err)
      }
    }

    // --- 5. Trigger DLT pipeline ---
    const pipelineId = sessionStorage.getItem('docubricks-dlt-pipeline-id')
    if (pipelineId) {
      try {
        await dbFetch(host, token, `/api/2.0/pipelines/${pipelineId}/updates`, {
          method: 'POST',
          body: JSON.stringify({ full_refresh: false }),
        })
      } catch (err) {
        console.warn('[DocuBricks] Could not trigger DLT pipeline update:', err)
      }
    } else {
      // Attempt to trigger via the ingestion job
      const jobId = await resolveJobIdByName(host, token, '03_ingest_document')
      if (jobId) {
        try {
          await dbFetch<DBRunResponse>(host, token, '/api/2.1/jobs/run-now', {
            method: 'POST',
            body: JSON.stringify({
              job_id: jobId,
              notebook_params: { document_id: documentId, catalog_name: catalogName },
            }),
          })
        } catch (err) {
          console.warn('[DocuBricks] Could not trigger ingestion job:', err)
        }
      }
    }

    onProgress({ documentId, documentType, status: 'processing' })

    // --- 6. Poll document_registry status every 2s ---
    if (!warehouseId) {
      // No warehouse available — return a synthetic processing result
      const result: DocumentProcessingResult = {
        documentId,
        documentType,
        status: 'processing',
        elapsedMs: Date.now(),
      }
      onProgress(result)
      return result
    }

    const startTime = Date.now()
    const pollSQL = `
      SELECT status, document_type, extraction_conf, extracted_fields
      FROM ${catalogName}.bronze.document_registry
      WHERE document_id = '${documentId}'
      LIMIT 1
    `

    const finalResult = await poll<DocumentProcessingResult>(
      async () => {
        await sleep(2000)
        try {
          const rows = await executeSQLStatement(host, token, warehouseId, pollSQL)
          if (!rows || rows.length === 0) return { done: false }

          const [statusVal, docTypeVal, confVal, fieldsJson] = rows[0]
          const status = statusVal?.toUpperCase()

          if (status === 'COMPLETE' || status === 'COMPLETED') {
            let fields: Record<string, string> | undefined
            try {
              fields = JSON.parse(fieldsJson ?? '{}')
            } catch {
              fields = {}
            }
            return {
              done: true,
              result: {
                documentId,
                documentType: docTypeVal ?? documentType,
                status: 'complete',
                confidence: parseFloat(confVal ?? '0') || undefined,
                fields,
                elapsedMs: Date.now() - startTime,
              },
            }
          }

          if (status === 'FAILED' || status === 'ERROR') {
            return {
              done: true,
              result: {
                documentId,
                documentType: docTypeVal ?? documentType,
                status: 'failed',
                elapsedMs: Date.now() - startTime,
              },
            }
          }

          // Still processing
          const intermediate: DocumentProcessingResult = {
            documentId,
            documentType: docTypeVal ?? documentType,
            status: 'processing',
            elapsedMs: Date.now() - startTime,
          }
          onProgress(intermediate)
          return { done: false }
        } catch (err) {
          console.warn('[DocuBricks] Status poll error:', err)
          return { done: false }
        }
      },
      2000,  // poll every 2s (sleep is inside the fn)
      150    // max ~5 minutes
    )

    onProgress(finalResult)
    return finalResult
  }
}

// ---------------------------------------------------------------------------
// SQL warehouse utilities
// ---------------------------------------------------------------------------

async function resolveWarehouseId(host: string, token: string): Promise<string | null> {
  try {
    const resp = await dbFetch<{
      warehouses?: Array<{ id: string; name: string; state: string }>
    }>(host, token, '/api/2.0/sql/warehouses')

    const warehouses = resp.warehouses ?? []
    // Prefer RUNNING warehouses, then any
    const running = warehouses.find((w) => w.state === 'RUNNING')
    if (running) return running.id
    if (warehouses.length > 0) return warehouses[0].id
    return null
  } catch {
    return null
  }
}

async function executeSQLStatement(
  host: string,
  token: string,
  warehouseId: string,
  sql: string
): Promise<Array<Array<string>>> {
  const submitResp = await dbFetch<SQLStatementResponse>(
    host,
    token,
    '/api/2.0/sql/statements',
    {
      method: 'POST',
      body: JSON.stringify({
        statement: sql,
        warehouse_id: warehouseId,
        wait_timeout: '30s',
        on_wait_timeout: 'CONTINUE',
      }),
    }
  )

  let statementId = submitResp.statement_id
  let state = submitResp.status.state

  // Poll until terminal state
  const terminalStates = ['SUCCEEDED', 'FAILED', 'CLOSED', 'CANCELED']
  while (!terminalStates.includes(state)) {
    await sleep(1500)
    const pollResp = await dbFetch<SQLStatementResponse>(
      host,
      token,
      `/api/2.0/sql/statements/${statementId}`
    )
    statementId = pollResp.statement_id
    state = pollResp.status.state

    if (state === 'FAILED' || state === 'CANCELED' || state === 'CLOSED') {
      const errMsg = pollResp.status.error?.message ?? `SQL statement ${state}`
      throw new Error(`SQL execution failed: ${errMsg}`)
    }

    if (state === 'SUCCEEDED') {
      return pollResp.result?.data_array ?? []
    }
  }

  if (state !== 'SUCCEEDED') {
    throw new Error(`SQL statement ended in state: ${state}`)
  }

  return submitResp.result?.data_array ?? []
}

// ---------------------------------------------------------------------------
// Legacy object-style export (matches existing src/api/index.ts import)
// ---------------------------------------------------------------------------

export const DatabricksRealAPI: DatabricksAPI = new DatabricksAPIImpl()
