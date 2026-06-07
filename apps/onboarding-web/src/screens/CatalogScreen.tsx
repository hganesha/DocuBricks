import { useState, useEffect, useCallback } from 'react'
import { ChevronRight, ChevronDown, Search, X, Database, FileJson, CheckCircle, Clock } from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────

interface SchemaEntry {
  vertical: string
  family: string
  family_display_name: string
  doc_type: string
  display_name: string
  priority: number
  availability: 'available' | 'future'
  rollout_status: string
  regulatory_alignment: string
}

interface CatalogData {
  schema_catalog_version: string
  document_types: SchemaEntry[]
}

type SchemaFile = 'fields' | 'validation_rules' | 'model_routing' | 'field_thresholds'

const FILE_TABS: { id: SchemaFile; label: string }[] = [
  { id: 'fields', label: 'Fields' },
  { id: 'validation_rules', label: 'Validation Rules' },
  { id: 'model_routing', label: 'Model Routing' },
  { id: 'field_thresholds', label: 'Field Thresholds' },
]

const VERTICAL_LABELS: Record<string, string> = {
  fs: 'Financial Services',
  healthcare: 'Healthcare',
  insurance: 'Insurance',
  legal: 'Legal',
  manufacturing: 'Manufacturing',
  real_estate: 'Real Estate',
}

const VERTICAL_ORDER = ['fs', 'healthcare', 'insurance', 'legal', 'manufacturing', 'real_estate']

// ─── JSON Syntax Highlighter ──────────────────────────────────────────────────

function highlight(json: string): string {
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      if (/^"/.test(match)) {
        if (/:$/.test(match)) return `<span class="json-key">${match}</span>`
        return `<span class="json-string">${match}</span>`
      }
      if (/true|false/.test(match)) return `<span class="json-bool">${match}</span>`
      if (/null/.test(match)) return `<span class="json-null">${match}</span>`
      return `<span class="json-number">${match}</span>`
    }
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function AvailabilityBadge({ availability }: { availability: string }) {
  if (availability === 'available') {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700">
        <CheckCircle size={9} />
        Registry ready
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-500">
      <Clock size={9} />
      Backlog
    </span>
  )
}

function JsonCanvas({ vertical, docType, file }: { vertical: string; docType: string; file: SchemaFile }) {
  const [content, setContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    setContent(null)
    fetch(`/schemas/${vertical}/${docType}/${file}.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data) => {
        setContent(JSON.stringify(data, null, 2))
        setLoading(false)
      })
      .catch((e) => {
        setError(e.message)
        setLoading(false)
      })
  }, [vertical, docType, file])

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
        Loading…
      </div>
    )
  }
  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center text-red-400 text-sm">
        Failed to load: {error}
      </div>
    )
  }

  return (
    <pre
      className="flex-1 overflow-auto p-5 text-[12.5px] leading-relaxed font-mono text-gray-800 bg-[#FAFAFA] rounded-b-lg border border-t-0 border-gray-200"
      dangerouslySetInnerHTML={{ __html: highlight(content || '') }}
    />
  )
}

// ─── Main Screen ──────────────────────────────────────────────────────────────

export default function CatalogScreen() {
  const [catalog, setCatalog] = useState<CatalogData | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [selectedVertical, setSelectedVertical] = useState<string>('fs')
  const [expandedFamilies, setExpandedFamilies] = useState<Set<string>>(new Set())
  const [selected, setSelected] = useState<SchemaEntry | null>(null)
  const [activeFile, setActiveFile] = useState<SchemaFile>('fields')

  useEffect(() => {
    fetch('/schemas/schema_catalog.json')
      .then((r) => r.json())
      .then((data: CatalogData) => {
        setCatalog(data)
        // Auto-expand first family of default vertical
        const firstFamily = data.document_types
          .filter((d) => d.vertical === 'fs')
          .map((d) => d.family)[0]
        if (firstFamily) setExpandedFamilies(new Set([`fs:${firstFamily}`]))
      })
      .catch((e) => setLoadError(e.message))
  }, [])

  const toggleFamily = useCallback((key: string) => {
    setExpandedFamilies((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }, [])

  const selectSchema = useCallback((entry: SchemaEntry) => {
    setSelected(entry)
    setActiveFile('fields')
  }, [])

  if (loadError) {
    return (
      <div className="min-h-screen flex items-center justify-center text-red-500">
        Failed to load catalog: {loadError}
      </div>
    )
  }

  if (!catalog) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400">
        <div className="w-5 h-5 rounded-full bg-accent-700 animate-pulse" />
      </div>
    )
  }

  const allDocs = catalog.document_types
  const lowerQuery = query.toLowerCase()

  // Build grouped structure for the selected vertical
  const verticalDocs = allDocs.filter((d) => {
    if (d.vertical !== selectedVertical) return false
    if (lowerQuery) {
      return (
        d.display_name.toLowerCase().includes(lowerQuery) ||
        d.family_display_name.toLowerCase().includes(lowerQuery)
      )
    }
    return true
  })

  const familyMap = new Map<string, SchemaEntry[]>()
  for (const d of verticalDocs) {
    const existing = familyMap.get(d.family) || []
    familyMap.set(d.family, [...existing, d])
  }

  const verticalCounts = VERTICAL_ORDER.reduce<Record<string, number>>((acc, v) => {
    acc[v] = allDocs.filter((d) => d.vertical === v).length
    return acc
  }, {})

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Top bar */}
      <header className="h-12 border-b border-gray-200 flex items-center px-5 gap-3 shrink-0">
        <Database size={16} className="text-accent-700" />
        <span className="font-semibold text-sm text-gray-900 tracking-tight">Schema Catalog</span>
        <span className="text-xs text-gray-400 ml-1">v{catalog.schema_catalog_version}</span>
        <span className="ml-2 px-2 py-0.5 rounded-full bg-accent-100 text-accent-700 text-[11px] font-semibold">
          {allDocs.length} schemas
        </span>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* ── Left sidebar ── */}
        <aside className="w-72 border-r border-gray-200 flex flex-col shrink-0 bg-gray-50">
          {/* Search */}
          <div className="p-3 border-b border-gray-200">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search schemas…"
                className="w-full pl-7 pr-7 py-1.5 text-xs rounded-md border border-gray-200 bg-white focus:outline-none focus:ring-1 focus:ring-accent-500 focus:border-accent-500"
              />
              {query && (
                <button onClick={() => setQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  <X size={12} />
                </button>
              )}
            </div>
          </div>

          {/* Vertical tabs */}
          <div className="flex flex-col gap-0.5 p-2 border-b border-gray-200">
            {VERTICAL_ORDER.map((v) => (
              <button
                key={v}
                onClick={() => setSelectedVertical(v)}
                className={`flex items-center justify-between w-full px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors text-left ${
                  selectedVertical === v
                    ? 'bg-accent-700 text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <span>{VERTICAL_LABELS[v]}</span>
                <span className={`text-[10px] font-normal ${selectedVertical === v ? 'text-accent-200' : 'text-gray-400'}`}>
                  {verticalCounts[v]}
                </span>
              </button>
            ))}
          </div>

          {/* Family accordion */}
          <div className="flex-1 overflow-y-auto py-2">
            {familyMap.size === 0 && (
              <p className="text-xs text-gray-400 px-4 py-3">No schemas match.</p>
            )}
            {Array.from(familyMap.entries()).map(([family, docs]) => {
              const key = `${selectedVertical}:${family}`
              const isOpen = expandedFamilies.has(key) || !!lowerQuery
              const displayName = docs[0].family_display_name
              const availableCount = docs.filter((d) => d.availability === 'available').length

              return (
                <div key={key} className="mb-0.5">
                  <button
                    onClick={() => toggleFamily(key)}
                    className="flex items-center gap-1.5 w-full px-3 py-1.5 text-left hover:bg-gray-100 transition-colors group"
                  >
                    {isOpen ? (
                      <ChevronDown size={13} className="text-gray-400 shrink-0" />
                    ) : (
                      <ChevronRight size={13} className="text-gray-400 shrink-0" />
                    )}
                    <span className="text-[11px] font-semibold text-gray-700 flex-1 truncate">
                      {displayName}
                    </span>
                    <span className="text-[10px] text-gray-400 shrink-0">
                      {availableCount}/{docs.length}
                    </span>
                  </button>

                  {isOpen && (
                    <div className="ml-6 border-l border-gray-200 pl-2 mb-1">
                      {docs.map((doc) => (
                        <button
                          key={doc.doc_type}
                          onClick={() => selectSchema(doc)}
                          className={`flex items-center gap-2 w-full px-2 py-1 rounded-md text-left transition-colors group ${
                            selected?.doc_type === doc.doc_type
                              ? 'bg-accent-50 text-accent-700'
                              : 'hover:bg-gray-100 text-gray-700'
                          }`}
                        >
                          <div
                            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                              doc.availability === 'available' ? 'bg-emerald-400' : 'bg-gray-300'
                            }`}
                          />
                          <span className="text-[11px] truncate flex-1">{doc.display_name}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </aside>

        {/* ── Right canvas ── */}
        <main className="flex-1 flex flex-col overflow-hidden bg-white">
          {!selected ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 text-gray-400">
              <FileJson size={40} strokeWidth={1} />
              <p className="text-sm">Select a schema to inspect its JSON</p>
            </div>
          ) : (
            <>
              {/* Schema header */}
              <div className="px-6 py-4 border-b border-gray-200 shrink-0">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-gray-400">
                        {VERTICAL_LABELS[selected.vertical]} › {selected.family_display_name}
                      </span>
                    </div>
                    <h1 className="text-base font-semibold text-gray-900">{selected.display_name}</h1>
                    <p className="text-[11px] font-mono text-gray-500 mt-0.5">{selected.doc_type}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1.5 shrink-0">
                    <AvailabilityBadge availability={selected.availability} />
                    {selected.priority === 1 && (
                      <span className="text-[10px] text-accent-700 font-medium">Priority 1</span>
                    )}
                  </div>
                </div>
                {selected.regulatory_alignment && (
                  <p className="text-[11px] text-gray-500 mt-2 bg-gray-50 rounded px-2 py-1 border border-gray-100">
                    {selected.regulatory_alignment}
                  </p>
                )}
              </div>

              {/* File tabs + JSON */}
              <div className="flex-1 flex flex-col overflow-hidden p-4 gap-0">
                {/* Tabs */}
                <div className="flex gap-0 border border-gray-200 rounded-t-lg overflow-hidden shrink-0">
                  {(selected.availability === 'available' ? FILE_TABS : FILE_TABS.slice(0, 1)).map((tab, i) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveFile(tab.id)}
                      disabled={selected.availability !== 'available'}
                      className={`px-4 py-2 text-xs font-medium transition-colors border-r border-gray-200 last:border-r-0 ${
                        activeFile === tab.id
                          ? 'bg-white text-accent-700 border-b-2 border-b-accent-600'
                          : 'bg-gray-50 text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                      } ${selected.availability !== 'available' && i > 0 ? 'opacity-40 cursor-not-allowed' : ''}`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* JSON canvas */}
                {selected.availability === 'available' ? (
                  <JsonCanvas
                    key={`${selected.vertical}/${selected.doc_type}/${activeFile}`}
                    vertical={selected.vertical}
                    docType={selected.doc_type}
                    file={activeFile}
                  />
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center gap-2 bg-[#FAFAFA] rounded-b-lg border border-t-0 border-gray-200 text-gray-400">
                    <Clock size={28} strokeWidth={1} />
                    <p className="text-sm">Schema bundle not yet available</p>
                    <p className="text-xs text-gray-300">Roadmap status: {selected.rollout_status}</p>
                  </div>
                )}
              </div>
            </>
          )}
        </main>
      </div>

      {/* JSON color token styles */}
      <style>{`
        .json-key    { color: #7C3AED; }
        .json-string { color: #059669; }
        .json-number { color: #D97706; }
        .json-bool   { color: #2563EB; }
        .json-null   { color: #9CA3AF; }
      `}</style>
    </div>
  )
}
