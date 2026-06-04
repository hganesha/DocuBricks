import type { DatabricksAPI } from '../interface'
import type { WorkspaceValidationResult, OnboardingConfig, DocumentProcessingResult } from '../../types'

const delay = (ms: number) => new Promise<void>((res) => setTimeout(res, ms))

// Realistic step durations (ms) — sum to ~45-55s
const STEP_DURATIONS: Record<string, number> = {
  verify_workspace:          800,
  create_service_principal:  1200,
  create_uc_schemas:         2000,
  upload_schema_registry:    3500,
  create_dlt_pipeline:       4000,
  provision_lakebase:        12000,   // longest
  run_db_migrations:         2500,
  create_genie_workspace:    3000,
  seed_genie:                2000,
  create_vector_index:       4500,
  deploy_portal_app:         3000,
  deploy_review_app:         2500,
  deploy_admin_app:          2000,
  write_secrets:             800,
  run_health_check:          1500,
}

// Simulated failure: set FAIL_STEP to a key to simulate a failure at that step
// In the mock, no steps fail by default (empty string = no failure)
const FAIL_STEP = ''

function generateSampleFields(docType: string): Record<string, string> {
  if (docType === 'mortgage_application') {
    return {
      'Borrower Name': 'John A. Smith',
      'Loan Amount': '$485,000',
      'Loan Purpose': 'Purchase',
      'Property Address': '1234 Oak Street, Austin TX 78701',
      'Debt-to-Income Ratio': '38.4%',
      'Credit Score': '742',
      'Interest Rate': '6.875%',
    }
  }
  if (docType === 'kyc_cdd_form') {
    return {
      'Customer Name': 'Acme Corporation Ltd.',
      'Customer Type': 'Business',
      'KYC Profile ID': 'KYC-2024-00891',
      'Risk Rating': 'Medium',
      'PEP Status': 'Not Applicable',
      'Jurisdiction': 'United States',
      'Industry': 'Technology',
    }
  }
  if (docType === 'aml_sar') {
    return {
      'Filing Type': 'Initial',
      'Suspicious Activity': 'Structuring',
      'Amount Involved': '$45,000',
      'Date of Activity': '2024-11-15',
      'Subject Name': '[REDACTED]',
    }
  }
  // Default: invoice
  return {
    'Vendor': 'TechSupply Inc.',
    'Invoice Number': 'INV-2024-4521',
    'Amount': '$12,450.00',
    'Due Date': '2024-12-01',
    'Line Items': '4 items',
  }
}

export const DatabricksMockAPI: DatabricksAPI = {
  async validateWorkspace(host: string, token: string): Promise<WorkspaceValidationResult> {
    // Simulate sequential validation steps (~2.5s total)
    await delay(400)  // connectivity check

    // Simulate error for clearly invalid inputs
    if (!host.includes('databricks') && !host.includes('localhost')) {
      await delay(300)
      return { connected: false, error: 'Could not connect. Check the workspace URL.' }
    }
    if (token.length < 4) {
      await delay(200)
      return { connected: false, error: 'Token is too short. Please check your personal access token.' }
    }

    await delay(600)  // UC check
    await delay(500)  // catalog scan
    await delay(400)  // plan detection

    // Detect cloud from URL pattern
    let cloud: 'azure' | 'aws' | 'gcp' | 'unknown' = 'unknown'
    let region = 'us-east-1'
    if (host.includes('azuredatabricks')) { cloud = 'azure'; region = 'eastus2' }
    else if (host.includes('gcp')) { cloud = 'gcp'; region = 'us-central1' }
    else if (host.includes('aws') || host.includes('databricks.com')) { cloud = 'aws'; region = 'us-east-1' }
    else if (host.includes('localhost')) { cloud = 'azure'; region = 'eastus2' }

    // Simulate detecting existing catalog ~50% of the time for demo purposes
    const existingCatalog = Math.random() > 0.5 ? 'docubricks_prod' : null

    return {
      connected: true,
      cloud,
      region,
      plan: 'premium',
      ucEnabled: true,
      existingCatalog,
    }
  },

  async provision(
    _config: OnboardingConfig,
    callbacks: {
      onStepStart: (key: string) => void
      onStepComplete: (key: string, elapsedMs: number) => void
      onStepFail: (key: string, error: string) => void
    }
  ): Promise<void> {
    const { onStepStart, onStepComplete, onStepFail } = callbacks
    const steps = Object.keys(STEP_DURATIONS)

    for (const key of steps) {
      const duration = STEP_DURATIONS[key]
      const started = Date.now()
      onStepStart(key)
      await delay(duration)

      if (key === FAIL_STEP) {
        onStepFail(key, 'Permission denied on catalog docubricks_prod. Grant USAGE + CREATE.')
        throw new Error('Provisioning failed')
      }

      onStepComplete(key, Date.now() - started)
    }
  },

  async processDocument(
    file: File | 'sample_kyc' | 'sample_mortgage' | 'sample_aml',
    _config: OnboardingConfig,
    onProgress: (result: DocumentProcessingResult) => void
  ): Promise<DocumentProcessingResult> {
    const docId = `doc_${Math.random().toString(36).slice(2, 10)}`

    // Determine document type from sample name or file name
    let docType = 'kyc_cdd_form'
    if (file === 'sample_mortgage') docType = 'mortgage_application'
    else if (file === 'sample_aml') docType = 'aml_sar'
    else if (file !== 'sample_kyc' && file instanceof File) {
      const name = file.name.toLowerCase()
      if (name.includes('mortgage') || name.includes('urla')) docType = 'mortgage_application'
      else if (name.includes('sar') || name.includes('aml')) docType = 'aml_sar'
      else if (name.includes('invoice')) docType = 'invoice'
    }

    onProgress({ documentId: docId, documentType: docType, status: 'processing' })
    await delay(1500)
    onProgress({ documentId: docId, documentType: docType, status: 'processing' })
    await delay(2000)
    onProgress({ documentId: docId, documentType: docType, status: 'processing' })
    await delay(2500)

    const result: DocumentProcessingResult = {
      documentId: docId,
      documentType: docType,
      status: 'complete',
      confidence: 0.87 + Math.random() * 0.12,
      elapsedMs: 6000,
      fields: generateSampleFields(docType),
    }
    onProgress(result)
    return result
  },
}
