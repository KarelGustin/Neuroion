'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getMembers } from '@/lib/api'

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

  useEffect(() => {
    fetchMembers()
  }, [])

  const fetchMembers = async () => {
    try {
      const data = await getMembers()
      setMembers(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch user:', err)
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
        <h1 className="text-4xl font-semibold mb-2">Profile</h1>
        <p className="text-muted">Single-user account</p>
      </header>

      <div className="space-y-4">
        {members.length === 0 ? (
          <div className="text-center py-12 text-muted">
            <p>No user configured yet. Complete setup first.</p>
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
