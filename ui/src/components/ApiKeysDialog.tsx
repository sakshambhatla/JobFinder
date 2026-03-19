import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getApiKeyStatus, storeApiKey, deleteApiKey, validateStoredApiKey } from "@/lib/api";

interface ApiKeysDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const PROVIDERS = [
  {
    id: "anthropic" as const,
    label: "Anthropic (Claude)",
    placeholder: "sk-ant-...",
    helpUrl: "https://console.anthropic.com",
  },
  {
    id: "gemini" as const,
    label: "Google Gemini",
    placeholder: "AIza...",
    helpUrl: "https://aistudio.google.com",
  },
];

export function ApiKeysDialog({ open, onOpenChange }: ApiKeysDialogProps) {
  const qc = useQueryClient();
  const { data: status } = useQuery({
    queryKey: ["api-key-status"],
    queryFn: getApiKeyStatus,
    enabled: open,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-md"
        style={{
          background: "rgba(15, 20, 30, 0.92)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderColor: "var(--glass-border)",
        }}
      >
        <DialogHeader>
          <DialogTitle>API Keys</DialogTitle>
        </DialogHeader>
        <p className="text-sm" style={{ color: "rgba(255,255,255,0.55)" }}>
          Store your own LLM API keys. Keys are encrypted at rest and never
          returned to the browser after saving.
        </p>
        <div className="flex flex-col gap-5 mt-2">
          {PROVIDERS.map((p) => (
            <ProviderRow
              key={p.id}
              provider={p.id}
              label={p.label}
              placeholder={p.placeholder}
              helpUrl={p.helpUrl}
              isStored={status?.[p.id] ?? false}
              onSuccess={() => qc.invalidateQueries({ queryKey: ["api-key-status"] })}
            />
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ProviderRow({
  provider,
  label,
  placeholder,
  helpUrl,
  isStored,
  onSuccess,
}: {
  provider: "anthropic" | "gemini";
  label: string;
  placeholder: string;
  helpUrl: string;
  isStored: boolean;
  onSuccess: () => void;
}) {
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [testOk, setTestOk] = useState(false);

  const storeMut = useMutation({
    mutationFn: () => storeApiKey(provider, key),
    onSuccess: () => {
      setKey("");
      setError("");
      setTestOk(false);
      onSuccess();
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail || "Failed to save key");
    },
  });

  const deleteMut = useMutation({
    mutationFn: () => deleteApiKey(provider),
    onSuccess: () => {
      setError("");
      setTestOk(false);
      onSuccess();
    },
  });

  const testMut = useMutation({
    mutationFn: () => validateStoredApiKey(provider),
    onSuccess: () => {
      setTestOk(true);
      setError("");
    },
    onError: (err: any) => {
      setTestOk(false);
      setError(err?.response?.data?.detail || "Key validation failed");
    },
  });

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">{label}</Label>
        <div className="flex items-center gap-2">
          {isStored ? (
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{
                background: "rgba(34, 197, 94, 0.15)",
                color: "rgb(74, 222, 128)",
              }}
            >
              Stored
            </span>
          ) : (
            <span
              className="text-xs"
              style={{ color: "rgba(255,255,255,0.40)" }}
            >
              Not set
            </span>
          )}
        </div>
      </div>

      <div className="flex gap-2">
        <Input
          type="password"
          placeholder={placeholder}
          value={key}
          onChange={(e) => {
            setKey(e.target.value);
            setError("");
          }}
          className="flex-1 text-sm"
        />
        <Button
          size="sm"
          onClick={() => storeMut.mutate()}
          disabled={!key.trim() || storeMut.isPending}
        >
          {storeMut.isPending ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
          ) : (
            "Save"
          )}
        </Button>
        {isStored && (
          <>
            <Button
              size="sm"
              variant="outline"
              onClick={() => { setTestOk(false); testMut.mutate(); }}
              disabled={testMut.isPending}
            >
              {testMut.isPending ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              ) : (
                "Test"
              )}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => deleteMut.mutate()}
              disabled={deleteMut.isPending}
            >
              Remove
            </Button>
          </>
        )}
      </div>

      {error && (
        <p className="text-xs" style={{ color: "rgb(248, 113, 113)" }}>
          {error}
        </p>
      )}
      {testOk && !error && (
        <p className="text-xs" style={{ color: "rgb(74, 222, 128)" }}>
          Key is valid.
        </p>
      )}

      <a
        href={helpUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs underline"
        style={{ color: "rgba(255,255,255,0.40)" }}
      >
        Get a key
      </a>
    </div>
  );
}
