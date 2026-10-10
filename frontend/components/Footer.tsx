import { siteConfig } from "@/lib/config";

export default function Footer() {
  return (
    <footer className="mt-16 border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-8 text-base text-muted sm:flex-row sm:items-center sm:justify-between">
        <p className="italic">{siteConfig.team}</p>
        <p className="data flex flex-wrap gap-x-3 gap-y-1">
          {siteConfig.stack.map((s) => (
            <span key={s}>{s}</span>
          ))}
        </p>
      </div>
    </footer>
  );
}
