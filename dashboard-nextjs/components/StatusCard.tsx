'use client'

interface StatusCardProps {
  title: string
  status: string
  details?: Record<string, string | number>
}

export default function StatusCard({ title, status, details }: StatusCardProps) {
  const getStatusColor = () => {
    const statusLower = status.toLowerCase()
    if (statusLower === 'connected' || statusLower === 'running' || statusLower === 'active' || statusLower === 'ok') {
      return 'bg-green-500'
    } else if (statusLower === 'error' || statusLower === 'failed' || statusLower === 'disconnected') {
      return 'bg-red-500'
    }
    return 'bg-yellow-500'
  }

  return (
    <div className="p-6 bg-[#111] border border-border rounded-xl">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="flex items-center gap-2 mb-4">
        <div className={`w-3 h-3 rounded-full ${getStatusColor()}`}></div>
        <span className="text-sm text-muted capitalize">{status}</span>
      </div>
      {details && (
        <div className="space-y-2">
          {Object.entries(details).map(([key, value]) => (
            <div key={key} className="flex justify-between text-sm">
              <span className="text-muted">{key}:</span>
              <span className="text-foreground">{value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
