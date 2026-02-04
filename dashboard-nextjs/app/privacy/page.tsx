'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getDeviceConfig } from '@/lib/api'

export default function PrivacyPage() {
  const [config, setConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    try {
      const data = await getDeviceConfig()
      setConfig(data)
    } catch (err) {
      console.error('Failed to fetch config:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-6 max-w-4xl mx-auto">
      <header className="mb-8">
        <Link href="/" className="text-muted hover:text-foreground mb-4 inline-block">
          ← Back to Dashboard
        </Link>
        <h1 className="text-4xl font-semibold mb-2">Privacy</h1>
        <p className="text-muted">Manage your data and privacy settings</p>
      </header>

      <div className="space-y-6">
        {/* Retention Policy */}
        <div className="p-6 bg-[#111] border border-border rounded-xl">
          <h3 className="text-lg font-semibold mb-4">Data Retention</h3>
          {config?.retention_policy ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted">Retention Period:</span>
                <span>{config.retention_policy.days || 'N/A'} days</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Auto Delete:</span>
                <span>{config.retention_policy.auto_delete ? 'Enabled' : 'Disabled'}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted">No retention policy configured</p>
          )}
        </div>

        {/* Export Data */}
        <div className="p-6 bg-[#111] border border-border rounded-xl">
          <h3 className="text-lg font-semibold mb-4">Export Data</h3>
          <p className="text-sm text-muted mb-4">Download all your data stored locally</p>
          <button className="px-4 py-2 bg-[#333] hover:bg-[#444] rounded-lg text-sm font-medium transition-colors">
            Export Data
          </button>
        </div>

        {/* Delete Data */}
        <div className="p-6 bg-[#111] border border-border rounded-xl">
          <h3 className="text-lg font-semibold mb-4 text-red-500">Delete Data</h3>
          <p className="text-sm text-muted mb-4">Permanently delete all your data</p>
          <button className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium transition-colors">
            Delete All Data
          </button>
        </div>
      </div>
    </div>
  )
}
