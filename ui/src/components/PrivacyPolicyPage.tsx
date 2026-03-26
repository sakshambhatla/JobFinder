import { Link } from "react-router-dom";

export function PrivacyPolicyPage() {
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
      <main className="flex-1 pt-32 pb-24 px-6">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-black font-headline tracking-tighter mb-4">
            Privacy <span style={{ color: "#a3a6ff" }}>Policy</span>
          </h1>
          <p className="text-xs uppercase tracking-widest mb-12" style={{ color: "#adaaaa", fontFamily: "Inter" }}>
            Effective March 25, 2026 · Lithodora Labs
          </p>

          <div className="flex flex-col gap-10" style={{ color: "#adaaaa", lineHeight: "1.75" }}>
            <section>
              <h2 className="text-lg font-bold text-slate-200 mb-3 uppercase tracking-widest" style={{ fontFamily: "Inter", fontSize: "0.75rem" }}>
                1. Introduction
              </h2>
              <p>
                Verdant AI is operated by Lithodora Labs ("we", "us", "our"). This Privacy Policy explains
                how we collect, use, and protect the information you provide when you join our waitlist at{" "}
                <span style={{ color: "#a3a6ff" }}>verdant.ai</span>. By submitting your email address, you
                agree to the practices described here.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold text-slate-200 mb-3 uppercase tracking-widest" style={{ fontFamily: "Inter", fontSize: "0.75rem" }}>
                2. Information We Collect
              </h2>
              <p>
                We collect only your <strong className="text-slate-300">email address</strong>, which you
                provide voluntarily when you join the waitlist. We do not collect any other personal
                information at this time.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold text-slate-200 mb-3 uppercase tracking-widest" style={{ fontFamily: "Inter", fontSize: "0.75rem" }}>
                3. How We Use Your Information
              </h2>
              <p>
                Your email address is used solely to notify you about Verdant AI's launch and product
                updates. We will never use your email for advertising, sell it to third parties, or share
                it for any purpose other than what is described in this policy.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold text-slate-200 mb-3 uppercase tracking-widest" style={{ fontFamily: "Inter", fontSize: "0.75rem" }}>
                4. Data Sharing
              </h2>
              <p>
                We do not sell, rent, or trade your information. Your email address is stored on secure
                cloud infrastructure. We do not share it with any third parties except as required by
                applicable law or legal process.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold text-slate-200 mb-3 uppercase tracking-widest" style={{ fontFamily: "Inter", fontSize: "0.75rem" }}>
                5. Data Retention
              </h2>
              <p>
                We retain your email address until you request removal or unsubscribe. You can request
                deletion at any time by contacting us at the address below.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold text-slate-200 mb-3 uppercase tracking-widest" style={{ fontFamily: "Inter", fontSize: "0.75rem" }}>
                6. Your Rights
              </h2>
              <p>
                You have the right to access the information we hold about you, request correction of
                inaccurate data, and request deletion of your information at any time. To exercise any
                of these rights, email us at{" "}
                <a
                  href="mailto:lithodoralabs@gmail.com"
                  className="no-underline hover:text-white transition-colors"
                  style={{ color: "#a3a6ff" }}
                >
                  lithodoralabs@gmail.com
                </a>
                .
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold text-slate-200 mb-3 uppercase tracking-widest" style={{ fontFamily: "Inter", fontSize: "0.75rem" }}>
                7. Security
              </h2>
              <p>
                We use industry-standard security measures to protect your information, including
                encryption in transit and at rest. While no system is completely secure, we take
                reasonable steps to safeguard your data.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold text-slate-200 mb-3 uppercase tracking-widest" style={{ fontFamily: "Inter", fontSize: "0.75rem" }}>
                8. Changes to This Policy
              </h2>
              <p>
                We may update this Privacy Policy from time to time. If we make material changes, we
                will notify you by email using the address you provided. Continued use of the waitlist
                after changes constitutes acceptance of the updated policy.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold text-slate-200 mb-3 uppercase tracking-widest" style={{ fontFamily: "Inter", fontSize: "0.75rem" }}>
                9. Contact
              </h2>
              <p>
                Questions about this policy? Reach us at{" "}
                <a
                  href="mailto:lithodoralabs@gmail.com"
                  className="no-underline hover:text-white transition-colors"
                  style={{ color: "#a3a6ff" }}
                >
                  lithodoralabs@gmail.com
                </a>
                .
              </p>
            </section>
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
