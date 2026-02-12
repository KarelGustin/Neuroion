import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Neuroion Dashboard',
  description: 'Local-first home intelligence platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
