import type { Metadata } from "next";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { siteConfig } from "@/lib/config";

export const metadata: Metadata = { title: `How it works · ${siteConfig.name}` };

export default function HowItWorks() {
  return (
    <>
    <PageHeader
      title="How it works"
      text="A short look at our approach, so you can judge the thinking and not just the screen."
    />
    <div className="mx-auto max-w-4xl px-5 pt-4">

      <section className="mt-10">
        <h2 className="script text-4xl text-teal">Our approach</h2>
        <ol className="mt-5 grid gap-5 sm:grid-cols-3">
          {siteConfig.approach.map((a, i) => (
            <li key={a.title} className="card p-6">
              <span className="data font-semibold text-teal">STEP {i + 1}</span>
              <h3 className="mt-1 text-xl font-bold text-teal-dark">{a.title}</h3>
              <p className="mt-2 text-ink/80">{a.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-14">
        <h2 className="script text-4xl text-teal">The flow</h2>
        <div className="card mt-5 flex flex-col items-stretch gap-3 p-6 sm:flex-row sm:items-center">
          {["Your input", "Next.js app", "FastAPI backend", "Gemini + pandas", "Answer with proof"].map((s, i, arr) => (
            <div key={s} className="flex flex-1 items-center gap-3">
              <div className="data flex-1 rounded-xl bg-sky px-3 py-3 text-center font-semibold text-teal-dark">{s}</div>
              {i < arr.length - 1 && <span className="hidden text-teal sm:block">→</span>}
            </div>
          ))}
        </div>
      </section>

      <section className="mt-14 grid gap-8 sm:grid-cols-2">
        <div>
          <h2 className="script text-4xl text-teal">Your data</h2>
          <p className="mt-3 text-lg text-ink/90">{siteConfig.privacy}</p>
        </div>
        <div>
          <h2 className="script text-4xl text-teal">Limits</h2>
          <ul className="mt-3 list-disc space-y-1 pl-6 text-lg text-ink/90">
            {siteConfig.limits.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mt-14 grid gap-8 sm:grid-cols-2">
        <div>
          <h2 className="script text-4xl text-teal">What is next</h2>
          <ul className="mt-3 list-disc space-y-1 pl-6 text-lg text-ink/90">
            {siteConfig.next.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="script text-4xl text-teal">Built with</h2>
          <p className="data mt-3 flex flex-wrap gap-2">
            {siteConfig.stack.map((s) => (
              <span key={s} className="rounded-full border border-teal/60 px-3 py-1 text-teal-dark">
                {s}
              </span>
            ))}
          </p>
        </div>
      </section>

      <div className="mt-14 text-center">
        <Link href="/app" className="btn btn-primary text-lg">
          See it in action
        </Link>
      </div>
    </div>
    </>
  );
}
