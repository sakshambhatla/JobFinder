import { useRole } from "@/contexts/RoleContext";

interface SideNavProps {
  activeItem?: string;
  onItemClick?: (id: string) => void;
}

const navItems = [
  { label: "Overview", icon: "dashboard", id: "overview" },
  { label: "Updates", icon: "bolt", id: "updates" },
  { label: "Pipeline", icon: "description", id: "pipeline" },
  { label: "Offers", icon: "assignment_turned_in", id: "offers" },
  { label: "Integrations", icon: "extension", id: "integrations" },
  { label: "Analytics", icon: "bar_chart", id: "analytics", minRole: "devtest" as const },
];

const WIRED_ITEMS = new Set(["pipeline", "offers", "analytics"]);

export function SideNav({ activeItem = "pipeline", onItemClick }: SideNavProps) {
  const { isAtLeast } = useRole();

  return (
    <aside className="hidden md:flex flex-col py-10 px-6 gap-4 h-full w-64 fixed left-0 top-20 bg-[#0e0e0e]">
      <div className="mb-8 px-2">
        <div className="text-[#a3a6ff] font-['Space_Grotesk'] text-sm uppercase tracking-widest mb-1">
          Verdant AI
        </div>
        <div className="text-[#adaaaa] text-[10px] uppercase tracking-[0.2em]">
          Career Personal Assistant
        </div>
      </div>

      <nav className="space-y-2">
        {navItems.map((item) => {
          if ("minRole" in item && item.minRole && !isAtLeast(item.minRole)) return null;
          const active = item.id === activeItem;
          const wired = WIRED_ITEMS.has(item.id);
          return (
            <button
              key={item.id}
              type="button"
              onClick={wired && onItemClick ? () => onItemClick(item.id) : undefined}
              className={`flex items-center gap-3 px-4 py-3 w-full text-left font-['Space_Grotesk'] text-sm uppercase tracking-widest transition-all ${
                wired ? "cursor-pointer" : "cursor-default opacity-50"
              } ${
                active
                  ? "text-[#a3a6ff] font-bold bg-[#1a1a1a] rounded-lg translate-x-1"
                  : wired
                    ? "text-[#adaaaa] hover:bg-[#1a1a1a] hover:text-white"
                    : "text-[#adaaaa]"
              }`}
            >
              <span
                className="material-symbols-outlined text-lg"
                style={active ? { fontVariationSettings: "'FILL' 1" } : undefined}
              >
                {item.icon}
              </span>
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
