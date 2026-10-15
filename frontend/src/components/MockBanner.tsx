import React from 'react'

interface MockBannerProps {
  isMock: boolean
}

export const MockBanner: React.FC<MockBannerProps> = ({ isMock }) => {
  if (!isMock) return null

  return (
    <aside
      role="alert"
      aria-label="Mock Data Warning"
      className="w-full bg-amber-500 text-black px-4 py-2 font-bold text-center tracking-wide shadow-sm flex items-center justify-center gap-2 text-sm uppercase"
    >
      <span>MOCK DATA, not model output</span>
    </aside>
  )
}
