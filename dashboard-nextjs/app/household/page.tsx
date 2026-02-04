'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getMembers, createJoinToken } from '@/lib/api'
import { QRCodeSVG } from 'qrcode.react'

interface Member {
  id: number
  name: string
  role: string
  language?: string
  timezone?: string
  created_at: string
}

export default function HouseholdPage() {
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [qrData, setQrData] = useState<{ url: string; token: string } | null>(null)
  const [creatingToken, setCreatingToken] = useState(false)

  useEffect(() => {
    fetchMembers()
  }, [])

  const fetchMembers = async () => {
    try {
      const data = await getMembers()
      setMembers(data)
    } catch (err) {
      console.error('Failed to fetch members:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAddMember = async () => {
    setCreatingToken(true)
    try {
      const tokenData = await createJoinToken()
      const hostname = typeof window !== 'undefined' ? window.location.hostname : 'neuroion.local'
      const url = `http://${hostname}/join?token=${tokenData.token}`
      setQrData({ url, token: tokenData.token })
    } catch (err) {
      console.error('Failed to create join token:', err)
      alert('Failed to create join token. Please try again.')
    } finally {
      setCreatingToken(false)
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
        <h1 className="text-4xl font-semibold mb-2">Household</h1>
        <p className="text-muted">Manage household members</p>
      </header>

      <div className="mb-6">
        <button
          onClick={handleAddMember}
          disabled={creatingToken}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {creatingToken ? 'Creating...' : 'Add Member'}
        </button>
      </div>

      {qrData && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center p-6 z-50" onClick={() => setQrData(null)}>
          <div className="bg-[#111] border border-border rounded-2xl p-8 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-2xl font-semibold mb-4">Scan to Join</h2>
            <div className="bg-white p-4 rounded-lg mb-4 flex justify-center">
              <QRCodeSVG value={qrData.url} size={300} level="H" includeMargin={true} />
            </div>
            <p className="text-sm text-muted text-center mb-4 break-all">{qrData.url}</p>
            <button
              onClick={() => setQrData(null)}
              className="w-full py-3 bg-[#333] hover:bg-[#444] rounded-lg font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}

      <div className="space-y-4">
        {members.length === 0 ? (
          <div className="text-center py-12 text-muted">
            <p>No members yet. Add a member to get started.</p>
          </div>
        ) : (
          members.map((member) => (
            <div key={member.id} className="p-6 bg-[#111] border border-border rounded-xl">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-semibold mb-1">{member.name}</h3>
                  <div className="text-sm text-muted space-y-1">
                    <div>Role: {member.role}</div>
                    {member.language && <div>Language: {member.language}</div>}
                    {member.timezone && <div>Timezone: {member.timezone}</div>}
                    <div>Joined: {new Date(member.created_at).toLocaleDateString()}</div>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
