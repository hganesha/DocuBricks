import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { OnboardingStep, OnboardingConfig, DeployStep } from '../types'

const STEP_ORDER: OnboardingStep[] = [
  'WELCOME',
  'PROJECT',
  'VERTICAL',
  'WORKSPACE',
  'RESOURCES',
  'REVIEW',
  'DEPLOYING',
  'FIRST_DOC',
  'COMPLETE',
]

const DEPLOY_STEPS_CONFIG: Array<{ key: string; label: string; detail?: string }> = [
  { key: 'verify_workspace',         label: 'Verifying workspace access' },
  { key: 'create_service_principal', label: 'Creating DocuBricks service principal' },
  { key: 'create_uc_schemas',        label: 'Creating Unity Catalog schemas' },
  { key: 'upload_schema_registry',   label: 'Uploading extraction schemas (4 document types)' },
  { key: 'create_dlt_pipeline',      label: 'Deploying DLT pipeline' },
  {
    key: 'provision_lakebase',
    label: 'Provisioning Lakebase',
    detail: 'Lakebase is warming up. This is the longest step.',
  },
  { key: 'run_db_migrations',        label: 'Running database migrations' },
  { key: 'create_genie_workspace',   label: 'Creating Genie workspace' },
  { key: 'seed_genie',               label: 'Seeding Genie with 20 seed questions' },
  { key: 'create_vector_index',      label: 'Creating Vector Search index' },
  { key: 'deploy_portal_app',        label: 'Deploying DocuBricks Portal' },
  { key: 'deploy_review_app',        label: 'Deploying Review & Correction UI' },
  { key: 'deploy_admin_app',         label: 'Deploying Admin console' },
  { key: 'write_secrets',            label: 'Writing secrets to secret scope' },
  { key: 'run_health_check',         label: 'Running health check' },
]

interface OnboardingStore {
  step: OnboardingStep
  config: Partial<OnboardingConfig>
  deployLog: DeployStep[]

  // Navigation
  goTo: (step: OnboardingStep) => void
  goNext: () => void
  goBack: () => void

  // Config
  updateProject: (patch: Partial<OnboardingConfig['project']>) => void
  setVertical: (vertical: string) => void
  updateWorkspace: (patch: Partial<OnboardingConfig['workspace']>) => void
  updateResources: (patch: Partial<OnboardingConfig['resources']>) => void

  // Deploy log
  initDeployLog: () => void
  startDeployStep: (key: string) => void
  completeDeployStep: (key: string, elapsedMs: number) => void
  failDeployStep: (key: string, error: string) => void

  // Reset
  reset: () => void
}

const initialState: Pick<OnboardingStore, 'step' | 'config' | 'deployLog'> = {
  step: 'WELCOME',
  config: {},
  deployLog: [],
}

export const useOnboardingStore = create<OnboardingStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      // Navigation
      goTo: (step) => set({ step }),

      goNext: () => {
        const { step } = get()
        const currentIndex = STEP_ORDER.indexOf(step)
        if (currentIndex < STEP_ORDER.length - 1) {
          set({ step: STEP_ORDER[currentIndex + 1] })
        }
      },

      goBack: () => {
        const { step } = get()
        const currentIndex = STEP_ORDER.indexOf(step)
        if (currentIndex > 0) {
          set({ step: STEP_ORDER[currentIndex - 1] })
        }
      },

      // Config updates — deep merge each nested object
      updateProject: (patch) =>
        set((state) => ({
          config: {
            ...state.config,
            project: {
              ...state.config.project,
              ...patch,
            } as OnboardingConfig['project'],
          },
        })),

      setVertical: (vertical) =>
        set((state) => ({
          config: {
            ...state.config,
            vertical,
          },
        })),

      updateWorkspace: (patch) =>
        set((state) => ({
          config: {
            ...state.config,
            workspace: {
              ...state.config.workspace,
              ...patch,
            } as OnboardingConfig['workspace'],
          },
        })),

      updateResources: (patch) =>
        set((state) => ({
          config: {
            ...state.config,
            resources: {
              ...state.config.resources,
              ...patch,
            } as OnboardingConfig['resources'],
          },
        })),

      // Deploy log
      initDeployLog: () =>
        set({
          deployLog: DEPLOY_STEPS_CONFIG.map((s) => ({
            key: s.key,
            label: s.label,
            status: 'pending',
            detail: s.detail,
          })),
        }),

      startDeployStep: (key) =>
        set((state) => ({
          deployLog: state.deployLog.map((step) =>
            step.key === key
              ? { ...step, status: 'running', startedAt: Date.now() }
              : step
          ),
        })),

      completeDeployStep: (key, elapsedMs) =>
        set((state) => ({
          deployLog: state.deployLog.map((step) =>
            step.key === key
              ? { ...step, status: 'complete', elapsedMs }
              : step
          ),
        })),

      failDeployStep: (key, error) =>
        set((state) => ({
          deployLog: state.deployLog.map((step) =>
            step.key === key
              ? { ...step, status: 'failed', error }
              : step
          ),
        })),

      // Reset to initial state
      reset: () => set({ ...initialState }),
    }),
    {
      name: 'docubricks-onboarding',
      storage: createJSONStorage(() => sessionStorage),
    }
  )
)
