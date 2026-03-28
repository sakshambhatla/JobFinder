import { useState, type FormEvent } from "react";
import { useAuth } from "@/components/AuthProvider";

export function LoginPage() {
  const { signIn, signUp, signInWithGoogle } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [signUpSuccess, setSignUpSuccess] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const result = isSignUp
      ? await signUp(email, password)
      : await signIn(email, password);

    setLoading(false);

    if (result) {
      setError(result);
    } else if (isSignUp) {
      setSignUpSuccess(true);
    }
  };

  return (
    <div className="landing-page min-h-screen flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Ambient background blobs */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full blur-[120px] pointer-events-none" style={{ background: "rgba(163, 166, 255, 0.1)" }} />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full blur-[100px] pointer-events-none" style={{ background: "rgba(83, 221, 252, 0.05)" }} />

      <main className="w-full max-w-[440px] z-10">
        {/* Brand identity */}
        <div className="flex flex-col items-center mb-10">
          <div className="mb-6 w-20 h-20 flex items-center justify-center">
            <img
              alt="Verdant AI Logo"
              src="/verdant-logo.png"
              className="w-full h-full object-contain"
            />
          </div>
          <h2 className="font-label text-xs tracking-[0.3em] uppercase mb-2" style={{ color: "#adaaaa" }}>
            Verdant AI
          </h2>
          <h1 className="text-3xl font-headline font-light tracking-tight text-center text-white">
            {isSignUp ? "Create your account" : "Sign in to your account"}
          </h1>
        </div>

        {/* Glass card */}
        <div className="lp-glass-panel ghost-border rounded-xl p-8 md:p-10 shadow-2xl">
          {signUpSuccess ? (
            <div className="text-center py-4">
              <p className="text-green-400 mb-2 font-headline">Account created!</p>
              <p style={{ color: "#adaaaa" }}>
                Check your email for a confirmation link, then sign in.
              </p>
              <button
                type="button"
                className="mt-4 font-label text-xs uppercase tracking-widest transition-colors hover:underline underline-offset-4"
                style={{ color: "#40ceed" }}
                onClick={() => {
                  setIsSignUp(false);
                  setSignUpSuccess(false);
                }}
              >
                Back to sign in
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Email */}
              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="font-label text-xs tracking-wider uppercase ml-1"
                  style={{ color: "#adaaaa" }}
                >
                  Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full ghost-border rounded-xl py-4 px-5 text-white placeholder:text-[rgba(118,117,117,0.5)] font-body transition-all login-input-glow"
                  style={{ background: "#131313" }}
                />
              </div>

              {/* Password */}
              <div className="space-y-2">
                <div className="flex justify-between items-center ml-1">
                  <label
                    htmlFor="password"
                    className="font-label text-xs tracking-wider uppercase"
                    style={{ color: "#adaaaa" }}
                  >
                    Password
                  </label>
                  <a
                    href="#"
                    className="text-[10px] font-label uppercase tracking-widest transition-colors hover:brightness-125"
                    style={{ color: "#40ceed" }}
                    onClick={(e) => e.preventDefault()}
                  >
                    Forgot?
                  </a>
                </div>
                <input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full ghost-border rounded-xl py-4 px-5 text-white placeholder:text-[rgba(118,117,117,0.5)] font-body transition-all login-input-glow"
                  style={{ background: "#131313" }}
                />
              </div>

              {/* Error */}
              {error && (
                <p className="text-sm" style={{ color: "#ff6e84" }}>{error}</p>
              )}

              {/* Primary CTA */}
              <button
                type="submit"
                disabled={loading}
                className="w-full pulse-gradient text-white font-headline font-bold py-4 rounded-full transition-all active:scale-[0.98] disabled:opacity-60 flex items-center justify-center"
                style={{
                  boxShadow: "0 8px 30px rgba(96, 99, 238, 0.3)",
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 12px 40px rgba(96, 99, 238, 0.5)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 8px 30px rgba(96, 99, 238, 0.3)"; }}
              >
                {loading && (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent mr-2" />
                )}
                {isSignUp ? "Create account" : "Sign in"}
              </button>

              {/* Divider */}
              <div className="relative py-4 flex items-center">
                <div className="flex-grow border-t" style={{ borderColor: "rgba(72, 72, 71, 0.2)" }} />
                <span className="flex-shrink mx-4 font-label text-[10px] uppercase tracking-[0.2em]" style={{ color: "#767575" }}>
                  or
                </span>
                <div className="flex-grow border-t" style={{ borderColor: "rgba(72, 72, 71, 0.2)" }} />
              </div>

              {/* Google */}
              <button
                type="button"
                disabled={loading}
                className="w-full ghost-border rounded-full py-4 px-6 flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:opacity-60"
                style={{ background: "rgba(44, 44, 44, 0.1)" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(44, 44, 44, 0.2)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(44, 44, 44, 0.1)"; }}
                onClick={async () => {
                  setError(null);
                  const err = await signInWithGoogle();
                  if (err) setError(err);
                }}
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                </svg>
                <span className="font-headline font-medium text-sm text-white">Continue with Google</span>
              </button>
            </form>
          )}
        </div>

        {/* Footer */}
        {!signUpSuccess && (
          <div className="mt-10 text-center">
            <p className="font-body text-sm" style={{ color: "#adaaaa" }}>
              {isSignUp ? "Already have an account?" : "Don't have an account?"}{" "}
              <button
                type="button"
                className="font-medium transition-colors ml-1 underline-offset-4 hover:underline"
                style={{ color: "#40ceed" }}
                onClick={() => {
                  setIsSignUp(!isSignUp);
                  setError(null);
                }}
              >
                {isSignUp ? "Sign in" : "Sign up"}
              </button>
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
