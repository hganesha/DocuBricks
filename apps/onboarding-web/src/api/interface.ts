import type { WorkspaceValidationResult, DocumentProcessingResult, OnboardingConfig } from '../types'

export interface DatabricksAPI {
  /**
   * Validates a Databricks workspace connection.
   * Checks connectivity, Unity Catalog, detects cloud/region/plan.
   */
  validateWorkspace(host: string, token: string): Promise<WorkspaceValidationResult>

  /**
   * Provisions all DocuBricks infrastructure.
   * Calls onStepStart/onStepComplete/onStepFail as each step progresses.
   * Returns when all steps are complete or throws on unrecoverable failure.
   */
  provision(
    config: OnboardingConfig,
    callbacks: {
      onStepStart: (key: string) => void
      onStepComplete: (key: string, elapsedMs: number) => void
      onStepFail: (key: string, error: string) => void
    }
  ): Promise<void>

  /**
   * Processes a document through the DocuBricks pipeline.
   * Polls until complete. Calls onProgress with status updates.
   */
  processDocument(
    file: File | 'sample_kyc' | 'sample_mortgage' | 'sample_aml',
    config: OnboardingConfig,
    onProgress: (result: DocumentProcessingResult) => void
  ): Promise<DocumentProcessingResult>
}

