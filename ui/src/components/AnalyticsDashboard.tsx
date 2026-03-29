import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAnalyticsSummary } from "@/lib/api";
import type { AnalyticsSummary } from "@/lib/api";
import { useRole } from "@/contexts/RoleContext";

const RANGE_OPTIONS = [
  { label: "7 days", value: 7 },
  { label: "30 days", value: 30 },
  { label: "90 days", value: 90 },
];

export function AnalyticsDashboard() {
  const [days, setDays] = useState(30);
  const { isAtLeast } = useRole();

  const { data, isLoading, error } = useQuery({
    queryKey: ["analytics-summary", days],
    queryFn: () => getAnalyticsSummary(days),
    staleTime: 5 * 60 * 1000,
    enabled: isAtLeast("devtest"),
  });

  if (!isAtLeast("devtest")) {
    return (
      <div className="flex items-center justify-center h-64 text-[#adaaaa]">
        You don't have permission to view analytics.
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white font-['Space_Grotesk']">
          Analytics
        </h1>
        <div className="flex gap-1 bg-[#1a1a1a] rounded-lg p-1">
          {RANGE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setDays(opt.value)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                days === opt.value
                  ? "bg-[#a3a6ff] text-black"
                  : "text-[#adaaaa] hover:text-white"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-48">
          <span className="h-6 w-6 animate-spin rounded-full border-2 border-[#a3a6ff] border-t-transparent" />
        </div>
      )}

      {error && (
        <div className="text-red-400 bg-red-400/10 rounded-lg p-4 text-sm">
          Failed to load analytics data.
        </div>
      )}

      {data && <AnalyticsContent data={data} />}
    </div>
  );
}

function AnalyticsContent({ data }: { data: AnalyticsSummary }) {
  return (
    <div className="space-y-8">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <SummaryCard label="Total Page Views" value={data.total_views} />
        <SummaryCard label="Unique Sessions" value={data.unique_sessions} />
        <SummaryCard label="Unique Users" value={data.unique_users} />
      </div>

      {/* Views Over Time */}
      {data.views_over_time.length > 0 && (
        <Section title="Views Over Time">
          <ViewsChart data={data.views_over_time} />
        </Section>
      )}

      {/* Views Per Page + Top Referrers side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {data.views_per_page.length > 0 && (
          <Section title="Pages">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#888] text-left text-xs uppercase tracking-wider">
                  <th className="pb-2">Path</th>
                  <th className="pb-2 text-right">Views</th>
                </tr>
              </thead>
              <tbody>
                {data.views_per_page.map((p) => (
                  <tr key={p.page} className="border-t border-[#222]">
                    <td className="py-2 text-[#ddd] font-mono text-xs">
                      {p.page}
                    </td>
                    <td className="py-2 text-right text-[#a3a6ff]">
                      {p.views.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}

        {data.top_referrers.length > 0 && (
          <Section title="Top Referrers">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#888] text-left text-xs uppercase tracking-wider">
                  <th className="pb-2">Referrer</th>
                  <th className="pb-2 text-right">Count</th>
                </tr>
              </thead>
              <tbody>
                {data.top_referrers.map((r) => (
                  <tr key={r.referrer} className="border-t border-[#222]">
                    <td className="py-2 text-[#ddd] text-xs truncate max-w-[200px]">
                      {r.referrer}
                    </td>
                    <td className="py-2 text-right text-[#a3a6ff]">
                      {r.count.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}
      </div>

      {data.total_views === 0 && (
        <div className="text-center text-[#888] py-12">
          No page views recorded yet for this time period.
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-[#1a1a1a] rounded-xl p-5 border border-[#222]">
      <div className="text-[#888] text-xs uppercase tracking-wider mb-1">
        {label}
      </div>
      <div className="text-3xl font-bold text-white font-['Space_Grotesk']">
        {value.toLocaleString()}
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-[#1a1a1a] rounded-xl p-5 border border-[#222]">
      <h2 className="text-sm font-medium text-[#adaaaa] uppercase tracking-wider mb-4">
        {title}
      </h2>
      {children}
    </div>
  );
}

function ViewsChart({
  data,
}: {
  data: Array<{ date: string; views: number }>;
}) {
  const maxViews = Math.max(...data.map((d) => d.views), 1);

  return (
    <div className="space-y-1">
      {data.map((d) => {
        const pct = (d.views / maxViews) * 100;
        const dateLabel = new Date(d.date + "T00:00:00").toLocaleDateString(
          undefined,
          { month: "short", day: "numeric" }
        );
        return (
          <div key={d.date} className="flex items-center gap-3 text-xs">
            <span className="w-16 text-right text-[#888] shrink-0">
              {dateLabel}
            </span>
            <div className="flex-1 bg-[#222] rounded-full h-5 overflow-hidden">
              <div
                className="bg-[#a3a6ff] h-full rounded-full transition-all"
                style={{ width: `${Math.max(pct, 2)}%` }}
              />
            </div>
            <span className="w-10 text-right text-[#adaaaa]">{d.views}</span>
          </div>
        );
      })}
    </div>
  );
}
