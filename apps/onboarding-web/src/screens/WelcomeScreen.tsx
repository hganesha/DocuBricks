import { useNavigate } from 'react-router-dom'
import { Button } from '../components'
import { useOnboardingStore } from '../store'

export default function WelcomeScreen() {
  const navigate = useNavigate()
  const store = useOnboardingStore()

  function handleGetStarted() {
    store.goTo('PROJECT')
    navigate('/project')
  }

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center">
      <div className="max-w-sm w-full px-6 text-center">
        {/* Logo */}
        <div className="text-4xl text-accent-700 mb-8 select-none">◈</div>

        {/* Title */}
        <h1 className="text-3xl font-semibold tracking-tighter text-gray-900">DocuBricks</h1>

        {/* Subtitles */}
        <p className="text-base text-gray-500 mt-3">Document intelligence, natively on Databricks.</p>
        <p className="text-sm text-gray-400 mt-1">Built for regulated industries.</p>

        {/* CTA */}
        <Button
          variant="primary"
          className="w-full mt-10"
          onClick={handleGetStarted}
        >
          Get started
        </Button>
      </div>

      {/* Version badge */}
      <div className="fixed bottom-4 right-4 text-xs text-gray-300">
        v0.1 · FS vertical
      </div>
    </div>
  )
}
