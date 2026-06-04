import { useState, useRef } from 'react'
import { CheckCircle2, Upload, XCircle } from 'lucide-react'
import { Button } from '../components'
import { useOnboardingStore } from '../store'
import { api } from '../api'
import type { DocumentProcessingResult } from '../types'
import { cn } from '../lib/utils'

function formatDocType(t: string) {
  return t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function FirstDocScreen() {
  const store = useOnboardingStore()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState<DocumentProcessingResult | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [, setUploadedFile] = useState<File | null>(null)

  async function handleFile(file: File | undefined) {
    if (!file) return
    setUploadedFile(file)
    setProcessing(true)
    setResult(null)
    const r = await api.processDocument(file, store.config as any, () => {})
    setResult(r)
    setProcessing(false)
  }

  async function handleSample(key: 'sample_kyc' | 'sample_mortgage' | 'sample_aml') {
    setProcessing(true)
    setResult(null)
    const r = await api.processDocument(key, store.config as any, () => {})
    setResult(r)
    setProcessing(false)
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <div
        className={cn(
          'flex-1 flex flex-col items-center',
          result ? 'justify-start pt-16' : 'justify-center'
        )}
      >
        {/* Initial state */}
        {!result && !processing && (
          <div className="w-full max-w-md px-6 text-center">
            {/* Success checkmark */}
            <div className="w-16 h-16 rounded-full bg-green-50 flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="w-8 h-8 text-green-500" />
            </div>

            <h1 className="text-2xl font-semibold tracking-tighter text-gray-900">
              DocuBricks is ready.
            </h1>
            <p className="text-sm text-gray-500 mt-2">
              Process your first document to see the full pipeline in action.
            </p>

            {/* Drop zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault()
                setDragOver(false)
                handleFile(e.dataTransfer.files[0])
              }}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                'mt-8 border-2 border-dashed rounded-xl p-10 cursor-pointer transition-colors',
                dragOver
                  ? 'border-accent-500 bg-accent-50'
                  : 'border-gray-200 hover:border-gray-300'
              )}
            >
              <Upload className="w-6 h-6 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-500">Drop a PDF here</p>
              <p className="text-xs text-gray-400 mt-1">or click to browse</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.png,.jpg"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0])}
              />
            </div>

            {/* Sample documents */}
            <div className="mt-6">
              <p className="text-xs text-gray-400 mb-3">Or use a pre-loaded sample:</p>
              <div className="flex flex-col gap-2">
                {[
                  { key: 'sample_kyc' as const, label: 'Sample KYC form (HSBC format, redacted)' },
                  {
                    key: 'sample_mortgage' as const,
                    label: 'Sample mortgage application (Fannie Mae URLA)',
                  },
                  { key: 'sample_aml' as const, label: 'Sample AML SAR' },
                ].map((s) => (
                  <button
                    key={s.key}
                    onClick={() => handleSample(s.key)}
                    className="text-left text-sm text-accent-700 hover:text-accent-800 py-1.5 px-3 rounded-lg hover:bg-accent-50 transition-colors"
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            <Button
              variant="ghost"
              className="mt-8 text-gray-400"
              onClick={() => store.goTo('COMPLETE')}
            >
              Skip → Go to Portal
            </Button>
          </div>
        )}

        {/* Processing state */}
        {processing && !result && (
          <div className="text-center max-w-sm px-6">
            <div className="w-8 h-8 border-2 border-accent-700 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-gray-900">Processing document...</h2>
            <p className="text-sm text-gray-400 mt-1">
              Running through Bronze → Silver → Gold pipeline
            </p>

            <div className="mt-6 flex flex-col gap-2 text-left max-w-xs mx-auto">
              {['Parsing document', 'Classifying type', 'Extracting fields', 'Validating schema'].map(
                (stage) => (
                  <div key={stage} className="flex items-center gap-2 text-sm text-gray-500">
                    <div className="w-1.5 h-1.5 rounded-full bg-accent-300 animate-pulse" />
                    {stage}
                  </div>
                )
              )}
            </div>
          </div>
        )}

        {/* Result state */}
        {result && result.status === 'complete' && (
          <div className="w-full max-w-md px-6">
            <div className="flex items-center gap-2 mb-6">
              <CheckCircle2 className="w-5 h-5 text-green-500" />
              <h2 className="text-lg font-semibold text-gray-900">Extraction complete</h2>
              <span className="ml-auto text-xs text-gray-400">
                {((result.confidence ?? 0) * 100).toFixed(0)}% confidence
              </span>
            </div>

            <div className="text-xs text-gray-400 mb-1">Document type</div>
            <div className="text-sm font-medium text-gray-900 mb-4">
              {formatDocType(result.documentType)}
            </div>

            <div className="text-xs text-gray-400 mb-2">Extracted fields</div>
            <div className="bg-gray-50 border border-gray-100 rounded-xl overflow-hidden">
              {Object.entries(result.fields ?? {}).map(([k, v], i) => (
                <div
                  key={k}
                  className={cn(
                    'flex justify-between px-4 py-2.5 text-sm',
                    i > 0 && 'border-t border-gray-100'
                  )}
                >
                  <span className="text-gray-500">{k}</span>
                  <span className="font-medium text-gray-900">{v}</span>
                </div>
              ))}
            </div>

            <div className="mt-8 flex gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => {
                  setResult(null)
                  setProcessing(false)
                }}
              >
                Process another
              </Button>
              <Button className="flex-1">Open Portal →</Button>
            </div>

            <p className="text-xs text-center text-gray-400 mt-4">
              Document ID: <span className="font-mono">{result.documentId}</span>
            </p>
          </div>
        )}

        {/* Failed state */}
        {result && result.status === 'failed' && (
          <div className="w-full max-w-md px-6 text-center">
            <div className="flex items-center justify-center gap-2 mb-4">
              <XCircle className="w-5 h-5 text-red-500" />
              <h2 className="text-lg font-semibold text-gray-900">Processing failed</h2>
            </div>
            <p className="text-sm text-gray-500 mb-6">
              We couldn't process this document. Try another file or use a sample.
            </p>
            <Button
              variant="secondary"
              onClick={() => {
                setResult(null)
                setProcessing(false)
              }}
            >
              Try again
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
