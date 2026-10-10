import Photo from "@/components/Photo";
import Link from "next/link";
import { images, siteConfig } from "@/lib/config";

export default function Home() {
  return (
    <>
      <section className="photo-bg">
        <Photo pic={images.hero} priority className="absolute inset-0 -z-10 h-full w-full object-cover" />
        <div className="mx-auto max-w-4xl px-5 pb-24 pt-20 text-center sm:pt-32">
          {siteConfig.label && (
            <p className="mb-4 text-sm uppercase tracking-[0.25em] text-muted">{siteConfig.label}</p>
          )}
          <h1 className="script text-6xl text-teal sm:text-8xl">{siteConfig.name}</h1>
          <p className="mx-auto mt-6 max-w-2xl text-xl text-ink sm:text-2xl">{siteConfig.tagline}</p>
          <div className="mt-9 flex flex-wrap justify-center gap-3">
            <Link href="/app" className="btn btn-primary text-lg">
              Try it now
            </Link>
            <Link href="/how-it-works" className="btn btn-ghost text-lg">
              How it works
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-5 pt-6">
        <h2 className="script text-4xl text-teal">The problem</h2>
        <p className="mt-3 text-xl leading-relaxed text-ink/85">{siteConfig.problem}</p>
      </section>

      <section className="mx-auto max-w-6xl px-5 pt-16">
        <h2 className="script text-center text-4xl text-teal">Three simple steps</h2>
        <ol className="mt-8 grid gap-5 sm:grid-cols-3">
          {siteConfig.steps.map((s, i) => (
            <li key={s.title} className="card overflow-hidden">
              <div className="p-6">
                <span className="script text-5xl text-teal">{i + 1}</span>
                <h3 className="mt-1 text-xl font-bold text-teal-dark">{s.title}</h3>
                <p className="mt-2 text-ink/85">{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="mt-10 text-center">
          <Link href="/app" className="btn btn-primary text-lg">
            Decode a bill
          </Link>
        </div>
      </section>
    </>
  );
}
