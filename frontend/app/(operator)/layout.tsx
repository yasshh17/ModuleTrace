import { Nav } from '@/components/nav'

export default function OperatorLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col min-h-screen">
      <Nav />
      <main className="flex-1 bg-muted/30">{children}</main>
    </div>
  )
}
