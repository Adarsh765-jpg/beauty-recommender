import { HealthProbe } from "@/components/health-probe";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#faf7f2] px-6 font-sans text-[#1a1614]">
      <main className="flex w-full max-w-xl flex-col gap-8">
        <div className="flex flex-col gap-3">
          <p className="text-xs uppercase tracking-[0.2em] text-[#8a7f76]">
            Phase 0 &middot; Deployment smoke test
          </p>
          <h1 className="text-4xl leading-tight font-medium tracking-tight">
            Beauty Recommender
          </h1>
          <p className="text-base leading-relaxed text-[#5c534c]">
            Scaffolding only. This page exists to prove that the Next.js frontend
            and the Python recommendation API deploy together as a single Vercel
            project, and that the browser can reach the API same-origin.
          </p>
        </div>

        <HealthProbe />
      </main>
    </div>
  );
}
