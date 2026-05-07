'use client'
import Link from 'next/link'
import { motion } from 'framer-motion'

const CARDS = [
  {
    href: '/latest-jobs/',
    icon: '💼',
    label: 'Latest Jobs',
    desc: 'All new notifications',
    gradient: 'from-violet-500 to-purple-700',
    glow: 'shadow-violet-500/30',
  },
  {
    href: '/results/',
    icon: '📊',
    label: 'Results',
    desc: 'Exam results & merit',
    gradient: 'from-emerald-400 to-teal-600',
    glow: 'shadow-emerald-500/30',
  },
  {
    href: '/admit-cards/',
    icon: '🪪',
    label: 'Admit Cards',
    desc: 'Hall tickets',
    gradient: 'from-sky-400 to-blue-600',
    glow: 'shadow-sky-500/30',
  },
  {
    href: '/answer-keys/',
    icon: '🔑',
    label: 'Answer Keys',
    desc: 'Official answers',
    gradient: 'from-amber-400 to-orange-600',
    glow: 'shadow-amber-500/30',
  },
  {
    href: '/syllabus/',
    icon: '📖',
    label: 'Syllabus',
    desc: 'Exam patterns',
    gradient: 'from-pink-400 to-rose-600',
    glow: 'shadow-pink-500/30',
  },
  {
    href: '/search/',
    icon: '🔍',
    label: 'Search',
    desc: 'Find anything',
    gradient: 'from-slate-400 to-slate-600',
    glow: 'shadow-slate-400/30',
  },
]

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.07 } },
}
const cardAnim = {
  hidden: { opacity: 0, y: 28, scale: 0.92 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
  },
}

export default function CategoryGrid() {
  return (
    <section className="py-8 sm:py-10">
      {/* Section heading */}
      <div className="max-w-7xl mx-auto px-4 mb-4">
        <h2 className="font-heading font-bold text-lg text-slate-700 flex items-center gap-2">
          <span className="w-1 h-5 rounded-full bg-amber-500 inline-block" />
          Browse Categories
        </h2>
      </div>

      {/* Mobile: horizontal pill scroll */}
      <motion.div
        variants={stagger}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        className="sm:hidden flex gap-3.5 overflow-x-auto scrollbar-none px-4 pb-2"
      >
        {CARDS.map((card) => (
          <motion.div key={card.href} variants={cardAnim} className="shrink-0">
            <Link
              href={card.href}
              className="flex flex-col items-center text-center w-[88px] gap-2"
            >
              <div
                className={`w-14 h-14 rounded-[18px] bg-gradient-to-br ${card.gradient} flex items-center justify-center text-2xl shadow-lg ${card.glow} transition-transform active:scale-90`}
              >
                {card.icon}
              </div>
              <span className="font-heading font-semibold text-[11px] text-slate-700 leading-tight">
                {card.label}
              </span>
            </Link>
          </motion.div>
        ))}
      </motion.div>

      {/* Desktop: 6-column grid */}
      <motion.div
        variants={stagger}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        className="hidden sm:grid sm:grid-cols-3 md:grid-cols-6 gap-4 px-4 max-w-7xl mx-auto"
      >
        {CARDS.map((card) => (
          <motion.div key={card.href} variants={cardAnim}>
            <Link
              href={card.href}
              className="group flex flex-col items-center text-center p-5 rounded-2xl bg-white border border-slate-100 hover:border-slate-200 hover:shadow-lg transition-all duration-300"
            >
              <div
                className={`w-14 h-14 rounded-[18px] bg-gradient-to-br ${card.gradient} flex items-center justify-center text-2xl shadow-md ${card.glow} group-hover:scale-110 transition-transform duration-300 mb-3`}
              >
                {card.icon}
              </div>
              <span className="font-heading font-bold text-sm text-slate-800">
                {card.label}
              </span>
              <span className="text-xs text-slate-400 mt-0.5">{card.desc}</span>
            </Link>
          </motion.div>
        ))}
      </motion.div>
    </section>
  )
}
