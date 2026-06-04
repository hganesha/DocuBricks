import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Input, Layout, RadioGroup } from '../components'
import { useOnboardingStore } from '../store'
import { slugify } from '../lib/utils'

export default function ProjectScreen() {
  const navigate = useNavigate()
  const store = useOnboardingStore()

  const [name, setName] = useState(store.config.project?.name ?? '')
  const [environment, setEnvironment] = useState<string>(
    store.config.project?.environment ?? 'production'
  )
  const [ownerEmail, setOwnerEmail] = useState(store.config.project?.ownerEmail ?? '')
  const [errors, setErrors] = useState<Record<string, string>>({})

  function validate(): boolean {
    const newErrors: Record<string, string> = {}

    if (!name || name.trim().length < 2) {
      newErrors.name = 'Project name must be at least 2 characters.'
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!ownerEmail || !emailRegex.test(ownerEmail.trim())) {
      newErrors.ownerEmail = 'Enter a valid email address.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function handleContinue() {
    if (!validate()) return
    store.updateProject({
      name: name.trim(),
      slug: slugify(name.trim()),
      environment: environment as 'production' | 'staging' | 'development',
      ownerEmail: ownerEmail.trim(),
    })
    navigate('/vertical')
  }

  return (
    <Layout step={1}>
      <h1 className="text-2xl font-semibold tracking-tighter text-gray-900">
        What are you building?
      </h1>
      <p className="text-sm text-gray-500 mt-1">
        Give your DocuBricks deployment a name.
      </p>

      <div className="flex flex-col gap-5 mt-8">
        <Input
          label="Project name"
          value={name}
          onChange={(v) => { setName(v); setErrors((e) => ({ ...e, name: '' })) }}
          placeholder="e.g. Acme Bank Document Intelligence"
          error={errors.name}
          autoFocus
        />

        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Environment
          </label>
          <RadioGroup
            layout="horizontal"
            value={environment}
            onChange={setEnvironment}
            options={[
              { value: 'production', label: 'Production' },
              { value: 'staging', label: 'Staging' },
              { value: 'development', label: 'Development' },
            ]}
          />
          <p className="text-xs text-gray-400 mt-2">
            Production uses liquid clustering, 90-day retention, and row-level security.
          </p>
        </div>

        <Input
          label="Owner email"
          type="email"
          value={ownerEmail}
          onChange={(v) => { setOwnerEmail(v); setErrors((e) => ({ ...e, ownerEmail: '' })) }}
          placeholder="you@company.com"
          error={errors.ownerEmail}
        />
      </div>

      <div className="flex justify-between items-center mt-10">
        <div />
        <Button onClick={handleContinue}>Continue →</Button>
      </div>
    </Layout>
  )
}
