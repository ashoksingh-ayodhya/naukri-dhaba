'use client'
import { useEffect } from 'react'
import Lenis from 'lenis'

export default function SmoothScroller({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const lenis = new Lenis({ lerp: 0.08, smoothWheel: true })
    let raf: number
    function frame(time: number) {
      lenis.raf(time)
      raf = requestAnimationFrame(frame)
    }
    raf = requestAnimationFrame(frame)
    return () => {
      cancelAnimationFrame(raf)
      lenis.destroy()
    }
  }, [])

  return <>{children}</>
}
