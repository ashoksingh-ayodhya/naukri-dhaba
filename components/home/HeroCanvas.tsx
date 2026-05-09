'use client'
import { useRef, useMemo, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function Particles({ color, count, spread, speed, reverseY = false }: {
  color: string
  count: number
  spread: [number, number, number]
  speed: number
  reverseY?: boolean
}) {
  const ref = useRef<THREE.Points>(null!)
  const pointer = useRef({ x: 0, y: 0 })

  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      pos[i * 3]     = (Math.random() - 0.5) * spread[0]
      pos[i * 3 + 1] = (Math.random() - 0.5) * spread[1]
      pos[i * 3 + 2] = (Math.random() - 0.5) * spread[2]
    }
    return pos
  }, [count, spread])

  useEffect(() => {
    const onPointer = (x: number, y: number) => {
      pointer.current.x = (x / window.innerWidth - 0.5) * 2
      pointer.current.y = -(y / window.innerHeight - 0.5) * 2
    }
    const onMouse  = (e: MouseEvent) => onPointer(e.clientX, e.clientY)
    const onTouch  = (e: TouchEvent) => onPointer(e.touches[0].clientX, e.touches[0].clientY)
    window.addEventListener('mousemove', onMouse)
    window.addEventListener('touchmove', onTouch, { passive: true })
    return () => {
      window.removeEventListener('mousemove', onMouse)
      window.removeEventListener('touchmove', onTouch)
    }
  }, [])

  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.elapsedTime
    ref.current.rotation.y = (reverseY ? -1 : 1) * t * speed + pointer.current.x * 0.07
    ref.current.rotation.x = Math.sin(t * 0.02) * 0.12 - pointer.current.y * 0.04
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.055}
        color={color}
        transparent
        opacity={0.7}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  )
}

function FloatingOrb({ pos, r, color, speed, phase }: {
  pos: [number, number, number]
  r: number
  color: string
  speed: number
  phase: number
}) {
  const ref = useRef<THREE.Mesh>(null!)
  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.elapsedTime
    ref.current.position.y = pos[1] + Math.sin(t * speed + phase) * 0.8
    ref.current.position.x = pos[0] + Math.cos(t * speed * 0.65 + phase) * 0.35
  })
  return (
    <mesh ref={ref} position={pos}>
      <sphereGeometry args={[r, 18, 18]} />
      <meshBasicMaterial color={color} transparent opacity={0.14} />
    </mesh>
  )
}

function Scene() {
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
  const gold  = isMobile ? 70  : 180
  const purple = isMobile ? 35  : 90

  return (
    <>
      <Particles color="#fbbf24" count={gold}   spread={[14, 8, 5]} speed={0.038} />
      <Particles color="#a855f7" count={purple}  spread={[16, 10, 5]} speed={0.022} reverseY />
      <FloatingOrb pos={[-3.5,  0.2, -3]} r={1.2} color="#f97316" speed={0.28} phase={0} />
      <FloatingOrb pos={[ 3.5,  0.0, -4]} r={1.5} color="#7c3aed" speed={0.20} phase={2.1} />
      <FloatingOrb pos={[-1.0,  2.2, -5]} r={0.9} color="#06b6d4" speed={0.38} phase={4.2} />
      <FloatingOrb pos={[ 2.2, -1.5, -2]} r={0.7} color="#fbbf24" speed={0.48} phase={1.0} />
    </>
  )
}

export default function HeroCanvas() {
  return (
    <Canvas
      camera={{ position: [0, 0, 5], fov: 65 }}
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
      gl={{
        antialias: false,
        alpha: true,
        powerPreference: 'low-power',
      }}
      dpr={[1, Math.min(typeof window !== 'undefined' ? window.devicePixelRatio : 1.5, 1.5)]}
    >
      <Scene />
    </Canvas>
  )
}
