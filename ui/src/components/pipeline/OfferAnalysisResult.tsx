import type { OfferAnalysis } from "@/lib/api";

const FLAG_COLORS = {
  green: "#22c55e",
  yellow: "#f59e0b",
  red: "#f43f5e",
} as const;

function scoreColor(score: number | null): string {
  if (score == null) return "text-white/30";
  if (score >= 3.5) return "text-emerald-400";
  if (score >= 2.5) return "text-yellow-400";
  return "text-rose-400";
}

function scoreBgColor(score: number | null): string {
  if (score == null) return "#6b7280";
  if (score >= 3.5) return "#22c55e";
  if (score >= 2.5) return "#f59e0b";
  return "#f43f5e";
}

function verdictLabel(score: number | null): string {
  if (score == null) return "No data";
  if (score >= 4.0) return "Strong offer — lean toward accepting";
  if (score >= 3.5) return "Solid offer — worth serious consideration";
  if (score >= 3.0) return "Mixed signals — negotiate hard and validate concerns";
  if (score >= 2.5) return "Below average — proceed with caution";
  return "Weak offer — consider alternatives";
}

export default function OfferAnalysisResult({ analysis }: { analysis: OfferAnalysis }) {
  const { dimensions, weighted_score, raw_average, flags, verdict, key_question } = analysis;

  return (
    <div className="space-y-5 mt-4">
      {/* ── Summary Row ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-3">
        {/* Weighted Score */}
        <div
          className="rounded-xl p-4 text-center border"
          style={{
            background: "rgba(255,255,255,0.05)",
            borderColor: "rgba(255,255,255,0.1)",
          }}
        >
          <div className="text-[11px] text-white/40 uppercase tracking-wider mb-2">
            Weighted score
          </div>
          <div className={`text-3xl font-bold tabular-nums ${scoreColor(weighted_score)}`}>
            {weighted_score?.toFixed(1) ?? "—"}
          </div>
        </div>

        {/* Raw Average */}
        <div
          className="rounded-xl p-4 text-center border"
          style={{
            background: "rgba(255,255,255,0.05)",
            borderColor: "rgba(255,255,255,0.1)",
          }}
        >
          <div className="text-[11px] text-white/40 uppercase tracking-wider mb-2">
            Raw average
          </div>
          <div className={`text-3xl font-bold tabular-nums ${scoreColor(raw_average)}`}>
            {raw_average?.toFixed(1) ?? "—"}
          </div>
        </div>

        {/* Flags */}
        <div
          className="rounded-xl p-4 text-center border"
          style={{
            background: "rgba(255,255,255,0.05)",
            borderColor: "rgba(255,255,255,0.1)",
          }}
        >
          <div className="text-[11px] text-white/40 uppercase tracking-wider mb-2">
            Flags
          </div>
          <div className="flex items-center justify-center gap-4 text-lg font-bold">
            {(["green", "yellow", "red"] as const).map((f) => (
              <span key={f} className="flex items-center gap-1.5">
                <span
                  className="inline-block w-2.5 h-2.5 rounded-full"
                  style={{ background: FLAG_COLORS[f] }}
                />
                <span className="tabular-nums text-white/70">{flags[f]}</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ── Progress Bar + Verdict ────────────────────────────────────── */}
      <div>
        <div
          className="h-2.5 rounded-full overflow-hidden"
          style={{ background: "rgba(255,255,255,0.08)" }}
        >
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${((weighted_score ?? 0) / 5) * 100}%`,
              background: scoreBgColor(weighted_score),
            }}
          />
        </div>
        <p className="text-sm text-white/50 mt-2 italic">
          {verdictLabel(weighted_score)}
        </p>
      </div>

      {/* ── Dimensions Grid ──────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {dimensions.map((dim) => (
          <div
            key={dim.name}
            className="rounded-lg p-3 border"
            style={{
              background: "rgba(255,255,255,0.04)",
              borderColor: "rgba(255,255,255,0.08)",
              borderLeftWidth: "3px",
              borderLeftColor: FLAG_COLORS[dim.flag as keyof typeof FLAG_COLORS] ?? "#6b7280",
            }}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[13px] font-semibold text-white/85">
                {dim.name}
              </span>
              <span className="flex items-center gap-1.5">
                {dim.weight > 1 && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/8 text-white/40 uppercase tracking-wider font-semibold">
                    1.5x
                  </span>
                )}
                <span
                  className="text-sm font-bold tabular-nums"
                  style={{ color: FLAG_COLORS[dim.flag as keyof typeof FLAG_COLORS] }}
                >
                  {dim.score}/5
                </span>
              </span>
            </div>
            {/* Score dots */}
            <div className="flex gap-1 mb-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="h-1.5 flex-1 rounded-full"
                  style={{
                    background:
                      i <= dim.score
                        ? FLAG_COLORS[dim.flag as keyof typeof FLAG_COLORS]
                        : "rgba(255,255,255,0.08)",
                  }}
                />
              ))}
            </div>
            <p className="text-[11px] text-white/45 leading-relaxed">
              {dim.rationale}
            </p>
          </div>
        ))}
      </div>

      {/* ── Verdict ──────────────────────────────────────────────────── */}
      {verdict && (
        <div
          className="rounded-lg p-4 border"
          style={{
            background: "rgba(255,255,255,0.04)",
            borderColor: "rgba(255,255,255,0.1)",
          }}
        >
          <div className="text-[11px] text-white/40 uppercase tracking-wider mb-2">
            Verdict
          </div>
          <p className="text-sm text-white/75 leading-relaxed">{verdict}</p>
        </div>
      )}

      {/* ── Key Question ─────────────────────────────────────────────── */}
      {key_question && (
        <div
          className="rounded-lg p-4 border"
          style={{
            background: `${FLAG_COLORS.yellow}08`,
            borderColor: `${FLAG_COLORS.yellow}33`,
          }}
        >
          <div className="text-[11px] uppercase tracking-wider mb-2" style={{ color: FLAG_COLORS.yellow }}>
            Key question for negotiation
          </div>
          <p className="text-sm text-white/75 leading-relaxed">{key_question}</p>
        </div>
      )}
    </div>
  );
}
