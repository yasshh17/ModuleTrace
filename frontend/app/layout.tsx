import type { Metadata } from 'next'
import { Inter } from 'next/font/google'

import { AuthProvider } from '@/app/lib/auth'
import { Providers } from '@/app/providers'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'ModuleTrace',
  description: 'Manufacturing quality traceability platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full bg-background text-foreground font-[family-name:var(--font-inter)]">
        <Providers>
          <AuthProvider>{children}</AuthProvider>
        </Providers>
      </body>
    </html>
  )
}
