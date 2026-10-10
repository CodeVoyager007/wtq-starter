import Photo, { type Pic } from "./Photo";

/** Dark photo banner with a title. Used at the top of the Decode a bill and How it works pages. */
export default function PageHeader({
  title,
  text,
  image,
}: {
  title: string;
  text: string;
  image: Pic;
}) {
  return (
    <section className="photo-bg">
      <Photo pic={image} priority className="absolute inset-0 -z-10 h-full w-full object-cover" />
      <div className="mx-auto max-w-6xl px-5 pb-12 pt-14 sm:pt-16">
        <h1 className="script text-5xl text-teal sm:text-7xl">{title}</h1>
        <p className="mt-3 max-w-2xl text-xl text-ink/90">{text}</p>
      </div>
    </section>
  );
}
