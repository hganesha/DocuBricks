export type OnboardingStep =
  | 'WELCOME'
  | 'PROJECT'
  | 'VERTICAL'
  | 'WORKSPACE'
  | 'RESOURCES'
  | 'REVIEW'
  | 'DEPLOYING'
  | 'FIRST_DOC'
  | 'COMPLETE'

export type Environment = 'production' | 'staging' | 'development'
export type Cloud = 'azure' | 'aws' | 'gcp' | 'unknown'
export type CatalogMode = 'existing' | 'create'
export type ComputeMode = 'serverless' | 'existing'
export type LakebaseMode = 'create' | 'existing'
export type GenieMode = 'create' | 'existing'

export interface ProjectConfig {
  name: string
  slug: string
  environment: Environment
  ownerEmail: string
}

export interface WorkspaceConfig {
  host: string
  cloud: Cloud
  region: string
  plan: string           // 'premium' | 'standard' | 'unknown'
  ucEnabled: boolean
  existingCatalog: string | null  // 'docubricks_prod' if detected
}

export interface ResourceConfig {
  catalogMode: CatalogMode
  catalogName: string
  computeMode: ComputeMode
  clusterId: string | null
  lakebaseMode: LakebaseMode
  lakebaseConnStr: string | null
  genieMode: GenieMode
  genieSpaceId: string | null
  genieName: string
}

export interface OnboardingConfig {
  project: ProjectConfig
  vertical: string           // 'fs' | 'healthcare' | 'legal' | 'insurance'
  workspace: WorkspaceConfig
  resources: ResourceConfig
}

export type DeployStepStatus = 'pending' | 'running' | 'complete' | 'failed'

export interface DeployStep {
  key: string
  label: string
  status: DeployStepStatus
  startedAt?: number        // Date.now()
  elapsedMs?: number
  error?: string
  detail?: string           // e.g. "Lakebase is warming up. This is the longest step."
}

export interface WorkspaceValidationResult {
  connected: boolean
  cloud?: Cloud
  region?: string
  plan?: string
  ucEnabled?: boolean
  existingCatalog?: string | null
  error?: string
}

export interface DocumentProcessingResult {
  documentId: string
  documentType: string
  status: 'processing' | 'complete' | 'failed'
  confidence?: number
  fields?: Record<string, string>
  elapsedMs?: number
}
