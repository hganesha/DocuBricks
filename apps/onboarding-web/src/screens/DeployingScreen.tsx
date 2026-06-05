import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { XCircle } from 'lucide-react'
import { Button, StepItem } from '../components'
import { useOnboardingStore } from '../store'
import { api } from '../api'
import type { OnboardingConfig } from '../types'

export default function DeployingScreen() {
  const navigate = useNavigate()
  const store = useOnboardingStore()
  const hasStarted = useRef(false)

  const [failed, setFailed] = useState(false)

  const startProvisioning = useCallback(async () => {
    setFailed(false)
    store.initDeployLog()
    try {
      await api.provision(store.config as OnboardingConfig, {
        onStepStart: (key) => store.startDeployStep(key),
        onStepComplete: (key, ms) => store.completeDeployStep(key, ms),
        onStepFail: (key, err) => store.failDeployStep(key, err),
      })
      setTimeout(() => navigate('/first-doc'), 1000)
    } catch {
      setFailed(true)
    }
  }, [navigate, store])

  useEffect(() => {
    if (hasStarted.current) return
    hasStarted.current = true
    startProvisioning()
  }, [startProvisioning])

  const deployLog = store.deployLog
  const currentStep = deployLog.find((s) => s.status === 'running')
  const failedStep = deployLog.find((s) => s.status === 'failed')

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-lg mx-auto px-6 py-16">
        <h1 className="text-2xl font-semibold tracking-tighter text-gray-900">
          Deploying DocuBricks.
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          This takes about 3–4 minutes. You'll be redirected automatically.
        </p>

        {/* Steps list */}
        <div className="mt-10 flex flex-col gap-1">
          {deployLog.map((step) => (
            <StepItem
              key={step.key}
              status={step.status}
              label={step.label}
              elapsedMs={step.elapsedMs}
              error={step.error}
            />
          ))}
        </div>

        {/* Contextual detail for the running step */}
        {currentStep?.detail && (
          <p className="mt-6 text-sm text-gray-400">{currentStep.detail}</p>
        )}

        {/* Failure card */}
        {failed && (
          <div className="mt-8 bg-red-50 border border-red-200 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="w-5 h-5 text-red-500 shrink-0" />
              <span className="text-sm font-semibold text-red-700">Deployment paused</span>
            </div>
            {failedStep?.error && (
              <p className="text-sm text-red-600 mb-4">{failedStep.error}</p>
            )}
            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={() => {
                  hasStarted.current = false
                  startProvisioning()
                }}
              >
                Retry from this step
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  store.reset()
                  navigate('/')
                }}
              >
                Start over
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
