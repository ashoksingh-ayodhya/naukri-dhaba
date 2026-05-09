'use client'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import { motion } from 'framer-motion'
import { CATEGORIES } from '@/config/site'

const HeroCanvas = dynamic(() => import('./HeroCanvas'), { ssr: false })

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
}
const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.65, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
  },
}

interface HeroProps {
  jobCount: number
  todayCount: number
}

export default function HeroSection({ jobCount, todayCount }: HeroProps) {
  return (
    <section
      className="relative flex flex-col items-center justify-center min-h-[100svh] overflow-hidden text-white"
      style={{ backgroundColor: '#06060f' }}
    >
      {/* Subtle grid overlay */}
      <div className="absolute inset-0 hero-grid pointer-events-none z-0" />

      {/* Radial purple glow behind text */}
      <div
        className="absolute inset-0 pointer-events-none z-0"
        style={{
          background:
            'radial-gradient(ellipse 80% 55% at 50% 55%, rgba(124,58,237,0.13) 0%, transparent 70%)',
        }}
      />

      {/* WebGL canvas */}
      <HeroCanvas />

      {/* Gradient fade into content below */}
      <div className="absolute bottom-0 left-0 right-0 h-36 bg-gradient-to-t from-slate-50 to-transparent pointer-events-none z-10" />

      {/* Hero content */}
      <motion.div
        className="relative z-10 w-full max-w-4xl mx-auto px-5 text-center py-20 pt-28"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* Live pill */}
        <motion.div variants={fadeUp} className="mb-6 flex justify-center">
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-sm font-semibold text-amber-400">
            <span className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
            {todayCount > 0 ? `${todayCount} new jobs posted today` : 'Updated daily from official sources'}
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          variants={fadeUp}
          className="font-heading font-bold text-4xl sm:text-5xl md:text-6xl lg:text-7xl leading-[1.06] tracking-tight mb-6"
        >
          <span className="text-white">Your Next </span>
          <span className="gradient-text">Sarkari Naukri</span>
          <br />
          <span className="text-white/85">Starts Here</span>
        </motion.h1>

        <motion.p
          variants={fadeUp}
          className="text-white/55 text-base sm:text-lg md:text-xl mb-8 max-w-2xl mx-auto leading-relaxed"
        >
          SSC · Railway · Banking · UPSC · Police · Defence — all in one place.{' '}
          <span className="text-white/70 font-medium">Zero ads. Zero fees.</span>
        </motion.p>

        {/* Glassmorphism search */}
        <motion.form
          variants={fadeUp}
          action="/search/"
          method="get"
          className="flex gap-2 max-w-lg mx-auto mb-9"
        >
          <label className="flex-1 flex items-center gap-2.5 px-4 py-3.5 glass rounded-2xl focus-within:border-amber-500/50 transition-all cursor-text">
            <svg
              className="w-4 h-4 text-white/35 shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              name="q"
              placeholder="Search SSC, Railway, Banking..."
              className="flex-1 bg-transparent text-white placeholder:text-white/35 text-sm outline-none"
            />
          </label>
          <button
            type="submit"
            className="px-5 py-3.5 bg-amber-500 hover:bg-amber-400 text-white font-bold rounded-2xl text-sm transition-all active:scale-95 shadow-lg shadow-amber-500/25 whitespace-nowrap"
          >
            Search
          </button>
        </motion.form>

        {/* Category pills — horizontal scroll on mobile */}
        <motion.div
          variants={fadeUp}
          className="flex gap-2 overflow-x-auto scrollbar-none pb-1 -mx-5 px-5 sm:mx-0 sm:px-0 sm:flex-wrap sm:justify-center mb-12"
        >
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.slug}
              href={`/jobs/${cat.slug}/`}
              className="shrink-0 inline-flex items-center gap-1.5 px-3.5 py-2 glass hover:bg-white/[0.15] rounded-full text-sm text-white/65 hover:text-white transition-all"
            >
              <span className="text-base leading-none">{cat.icon}</span>
              <span>{cat.label}</span>
            </Link>
          ))}
        </motion.div>

        {/* Stats */}
        <motion.div
          variants={fadeUp}
          className="grid grid-cols-3 gap-3 max-w-xs mx-auto"
        >
          {[
            { value: `${jobCount}+`, label: 'Active Posts' },
            { value: 'Daily', label: 'Updates' },
            { value: '100%', label: 'Free' },
          ].map((stat) => (
            <div
              key={stat.label}
              className="text-center py-3.5 px-2 rounded-2xl glass"
            >
              <div className="text-xl font-heading font-bold text-amber-400 leading-tight">
                {stat.value}
              </div>
              <div className="text-[10px] text-white/40 mt-0.5 uppercase tracking-wide">
                {stat.label}
              </div>
            </div>
          ))}
        </motion.div>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-10 left-1/2 -translate-x-1/2 z-10 flex flex-col items-center gap-1.5"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.4, duration: 0.6 }}
      >
        <span className="text-white/25 text-[9px] uppercase tracking-[0.2em]">Scroll</span>
        <div className="w-5 h-8 rounded-full border border-white/15 flex items-start justify-center pt-1.5">
          <motion.div
            className="w-1 h-1.5 bg-white/35 rounded-full"
            animate={{ y: [0, 12, 0] }}
            transition={{ repeat: Infinity, duration: 1.6, ease: 'easeInOut' }}
          />
        </div>
      </motion.div>
    </section>
  )
}
