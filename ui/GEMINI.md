# ui — Gemini Context

React 18 + TypeScript + Vite frontend for JobFinder.

## Dev Workflow
```bash
# Node 20+
pnpm install        # setup
pnpm dev            # dev server (localhost:5173, proxy /api → :8000)
pnpm build          # build to ui/dist/ (served by `jobfinder serve`)
```

## File Map
```
src/
  main.tsx              # React root
  App.tsx               # Main shell with Tabs
  lib/
    api.ts              # axios client + TypeScript types + fetch functions
    queryClient.ts      # TanStack Query client (staleTime=5m, retry=1)
  components/
    ResumeTab.tsx        # Resume upload & skills display
    CompaniesTab.tsx     # Company discovery and management
    RolesTab.tsx         # Role filtering, scoring, and sorting table
    ui/                  # shadcn/ui components
vite.config.ts           # proxy and alias config
tailwind.config.js       # styling configuration
```

## Key Patterns

**TanStack Query**:
- `useQuery` for all GET requests to ensure caching and loading state management.
- `useMutation` for all POST/PUT/DELETE requests.
- Always use `queryClient.setQueryData` after mutations for instant UI updates.

**API client (`lib/api.ts`)**:
- All API types and interaction functions are centralized here.
- Any backend change in `storage/schemas.py` or API routes must be reflected in the types and functions here.

**UI Components**:
- Use shadcn/ui primitives.
- Add new components via `pnpm dlx shadcn@latest add <component>`.

**Table Management**:
- `RolesTab` uses `@tanstack/react-table` for robust sorting and column management.

## Adding a New Tab
1. Implement the new tab component in `src/components/`.
2. Update `src/lib/api.ts` with new backend interaction logic.
3. Register the new tab in `App.tsx` within the `<Tabs>` structure.
