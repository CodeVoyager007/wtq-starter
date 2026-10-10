/** Site text and settings. The pages read everything from here. */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Pictures. Each one loads a real Unsplash photo (free to use, needs internet). If it cannot load,
 * the local generated image in frontend/public/images is shown instead, so the page never looks broken.
 * To swap a photo: change the `src` link, or replace the local file named in `fallback`.
 * Photo credits: see public/images/CREDITS.txt
 */
export const images = {
  hero: { src: "https://images.unsplash.com/photo-1609079332148-ce057e967197?auto=format&fit=crop&w=2000&q=75", fallback: "/images/hero.jpg", alt: "Sunlight filtering through deep blue ocean water" },
  headerHow: { src: "https://images.unsplash.com/photo-1783825772143-a2affdca150f?auto=format&fit=crop&w=2000&q=75", fallback: "/images/header-how.jpg", alt: "Dark blue water with small ripples" },
  headerWorkspace: { src: "https://images.unsplash.com/photo-1786311577577-897df260bf34?auto=format&fit=crop&w=2000&q=75", fallback: "/images/header-workspace.jpg", alt: "Deep blue water ripples" },
  steps: [
    { src: "https://images.unsplash.com/photo-1549074862-6173e20d02a8?auto=format&fit=crop&w=900&q=75", fallback: "/images/step-1.jpg", alt: "Bubbles rising through blue water" },
    { src: "https://images.unsplash.com/photo-1476897017502-219c9169bd6f?auto=format&fit=crop&w=900&q=75", fallback: "/images/step-2.jpg", alt: "Rippling blue ocean surface" },
    { src: "https://images.unsplash.com/photo-1764848084652-66719e701262?auto=format&fit=crop&w=900&q=75", fallback: "/images/step-3.jpg", alt: "Abstract blue textured background" },
  ],
  empty: { src: "https://images.unsplash.com/photo-1672577979719-450e2e75a689?auto=format&fit=crop&w=1000&q=75", fallback: "/images/empty.jpg", alt: "Dark blue ocean water with small waves" },
};

export const siteConfig = {
  name: "Bill Decoder",
  label: "AI electricity bill assistant", // small line above the title on Home. Leave "" to hide it
  tagline: "Upload your K-Electric, LESCO or IESCO bill and understand every rupee, in plain English.",
  problem:
    "Electricity bills in Pakistan mix tariff slabs, fuel adjustments, taxes and arrears, and every provider lays them out differently. Most people cannot tell what they are paying for, whether it is right, or what happens if they pay late.",
  steps: [
    { title: "Upload your bill", text: "A photo or screenshot is enough, even if it is tilted or partly in Urdu." },
    { title: "We read and check it", text: "Every amount, date and charge is extracted and checked against the bill's own totals." },
    { title: "Ask anything", text: "Get clear answers with the numbers worked out: taxes, late fees, usage trends, estimates." },
  ],
  approach: [
    { title: "Read the bill twice", text: "Gemini extracts the billing fields, and a second, independent pass transcribes everything printed on the bill." },
    { title: "Check with code", text: "Code normalises numbers and dates and checks the bill's own sums. Anything that does not add up, or is missing from the second reading, triggers a re-read." },
    { title: "Answer with real maths", text: "For questions, the model explains and writes the calculations; Python computes every number, so answers are exact and grounded in the bill." },
  ],
  privacy:
    "Bills stay in memory on the server for this session only. Names, addresses, account and meter numbers are never extracted or shown.",
  limits: [
    "Values hidden by grey boxes or too blurry to read are reported as not shown, never guessed.",
    "Answers use only what is printed on the bill, not outside tariff tables.",
    "Layout guides cover K-Electric, LESCO and IESCO bills.",
  ],
  next: ["Compare two bills side by side", "Urdu answers", "Alerts when a bill looks unusual"],
  stack: ["Next.js", "Tailwind CSS", "FastAPI", "Python", "Pillow", "Gemini 3.5 Flash-Lite"],
  team: "Made by Ayesha Mughal",
};
