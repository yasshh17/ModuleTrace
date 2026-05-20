import { Nav } from '@/components/nav'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen">
      <Nav />
      <main className="flex-1">{children}</main>
    </div>
  )
}
