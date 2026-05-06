import Link from "next/link";

const GRID_CARDS = [
  { href: "/latest-jobs/", icon: "💼", label: "Latest Jobs", desc: "All new job notifications", color: "bg-blue-50 border-blue-200 hover:border-blue-400" },
  { href: "/results/", icon: "📊", label: "Results", desc: "Exam results & merit lists", color: "bg-green-50 border-green-200 hover:border-green-400" },
  { href: "/admit-cards/", icon: "🪪", label: "Admit Cards", desc: "Hall tickets & call letters", color: "bg-purple-50 border-purple-200 hover:border-purple-400" },
  { href: "/answer-keys/", icon: "🔑", label: "Answer Keys", desc: "Official answer keys", color: "bg-orange-50 border-orange-200 hover:border-orange-400" },
  { href: "/syllabus/", icon: "📖", label: "Syllabus", desc: "Exam patterns & syllabus", color: "bg-pink-50 border-pink-200 hover:border-pink-400" },
  { href: "/search/", icon: "🔍", label: "Search", desc: "Find any job or result", color: "bg-slate-50 border-slate-200 hover:border-slate-400" },
];

export default function CategoryGrid() {
  return (
    <section className="max-w-7xl mx-auto px-4 py-8">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        {GRID_CARDS.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className={`flex flex-col items-center text-center p-4 rounded-xl border-2 transition-all hover:shadow-md ${card.color}`}
          >
            <span className="text-3xl mb-2">{card.icon}</span>
            <span className="font-heading font-bold text-sm text-slate-800">{card.label}</span>
            <span className="text-xs text-slate-500 mt-0.5 hidden sm:block">{card.desc}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
