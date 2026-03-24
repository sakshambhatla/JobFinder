import { Link } from "react-router-dom";

export function AboutPage() {
  return (
    <div className="landing-page min-h-screen flex flex-col">
      {/* ── Nav ── */}
      <nav className="fixed top-0 w-full z-50 backdrop-blur-md" style={{ background: "rgba(19,19,19,0.5)" }}>
        <div className="flex justify-between items-center max-w-7xl mx-auto px-6 py-4 w-full">
          <Link to="/" className="text-xl font-bold tracking-tighter text-slate-100 font-headline no-underline">
            Verdant AI
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/app" className="text-slate-400 hover:text-white transition-colors font-medium text-sm no-underline">
              Log In
            </Link>
            <Link
              to="/"
              className="pulse-gradient px-6 py-2 rounded-[0.75rem] font-bold text-sm no-underline"
              style={{ color: "#0f00a4" }}
            >
              Join Waitlist
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Content ── */}
      <main className="flex-1 flex items-center justify-center pt-20 px-6">
        <div className="max-w-2xl text-center">
          <h1 className="text-4xl md:text-6xl font-black font-headline tracking-tighter mb-8">
            About <span style={{ color: "#a3a6ff" }}>Verdant AI</span>
          </h1>

          <p className="text-lg leading-relaxed mb-8" style={{ color: "#adaaaa" }}>
            Verdant AI is built with love in Seattle, WA, to help job seekers find the roles they love.
            We believe that finding your next career move shouldn't feel like a second full-time job.
          </p>

          <p className="text-lg leading-relaxed mb-12" style={{ color: "#adaaaa" }}>
            Our mission is to be the intelligent layer between you and the job market — understanding your
            experience, preferences, and goals to surface the opportunities that truly matter.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
            <a
              href="https://github.com/sakshambhatla/VerdantMe/tree/main"
              target="_blank"
              rel="noopener noreferrer"
              className="lp-glass-panel px-8 py-4 rounded-[0.75rem] font-bold text-lg hover:bg-white/5 transition-all text-white no-underline"
            >
              View on GitHub
            </a>
            <Link
              to="/"
              className="font-label text-sm uppercase tracking-widest pb-1 no-underline transition-colors"
              style={{ color: "#40ceed", borderBottom: "1px solid rgba(83,221,252,0.3)" }}
            >
              Back to Home
            </Link>
          </div>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="w-full py-12 px-8" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
        <div className="flex flex-col md:flex-row justify-between items-center gap-4 max-w-7xl mx-auto w-full">
          <p className="text-xs uppercase tracking-widest text-slate-500" style={{ fontFamily: "Inter" }}>
            &copy; 2026 Lithodora Labs.
          </p>
          <div className="flex gap-8 text-xs uppercase tracking-widest" style={{ fontFamily: "Inter" }}>
            <Link to="/" className="text-slate-500 hover:text-white transition-colors no-underline">Home</Link>
            <Link to="/app" className="text-slate-500 hover:text-white transition-colors no-underline">App</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
