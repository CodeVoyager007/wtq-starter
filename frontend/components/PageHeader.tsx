/** Page title banner with the ember glow. Used at the top of the Decode a bill and How it works pages. */
export default function PageHeader({ title, text }: { title: string; text: string }) {
  return (
    <section className="photo-bg">
      <div className="mx-auto max-w-6xl px-5 pb-12 pt-14 sm:pt-16">
        <h1 className="script text-5xl sm:text-7xl">{title}</h1>
        <p className="mt-3 max-w-2xl text-xl text-ink/90">{text}</p>
      </div>
    </section>
  );
}
