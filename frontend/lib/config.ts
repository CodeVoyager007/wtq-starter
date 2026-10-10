/**
 * EVENT DAY: edit the text in this file first (10 minutes), the pages read everything from here.
 */
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
  name: "Project Name",
  label: "AI-powered tool", // small line above the title on Home. Leave "" to hide it
  tagline: "One clear sentence that says what your app does and who it helps.",
  problem:
    "Describe the problem from the challenge in two or three simple sentences. Who has this problem, and why does it matter?",
  steps: [
    { title: "Add your data", text: "Upload a file or paste text. Nothing to set up." },
    { title: "Ask or run", text: "Pick what you want to do and press Run. The AI does the heavy work." },
    { title: "Get clear answers", text: "See a short answer, a table, a chart, and the proof behind it." },
  ],
  approach: [
    { title: "Understand the data", text: "We look at the columns, types and missing values before anything else." },
    { title: "Let the model reason", text: "Gemini reads a short summary of the data and writes the steps to answer the question." },
    { title: "Check and show", text: "We run the steps, check the result, and show the answer with the code or sources used." },
  ],
  privacy:
    "Files stay in memory on the server for this session only. Nothing is saved to a database, and files are gone when the server restarts.",
  limits: [
    "Answers depend on the quality of the uploaded data.",
    "AI models can be wrong, so important results should be double checked.",
    "Large files are trimmed to keep responses fast.",
  ],
  next: ["Add user accounts and saved projects", "Support more file types", "Add scheduled reports"],
  stack: ["Next.js", "Tailwind CSS", "FastAPI", "Python", "pandas", "scikit-learn", "Google Gemini"],
  team: "Made by Ayesha Mughal",
};

export type ModeId = "analyze" | "docs" | "extract" | "classify" | "predict" | "custom";

export const modes: {
  id: ModeId;
  label: string;
  hint: string;
  placeholder: string;
  needs?: "dataset" | "docs";
}[] = [
  {
    id: "analyze",
    label: "Analyze data",
    hint: "Ask a question about your table in plain English.",
    placeholder: "Which city has the slowest average response time?",
    needs: "dataset",
  },
  {
    id: "docs",
    label: "Ask documents",
    hint: "Ask about the text files or PDFs you uploaded. Answers come with sources.",
    placeholder: "What is the refund policy?",
    needs: "docs",
  },
  {
    id: "extract",
    label: "Extract fields",
    hint: "Pull structured fields out of messy text (paste text, or name a text column).",
    placeholder: "Paste some text here...",
  },
  {
    id: "classify",
    label: "Classify text",
    hint: "Sort text into your own labels (paste text, or name a text column).",
    placeholder: "Paste some text here...",
  },
  {
    id: "predict",
    label: "Predict",
    hint: "Train a quick model to predict one column from the others.",
    placeholder: "",
    needs: "dataset",
  },
  {
    id: "custom",
    label: "Custom",
    hint: "Runs solve_challenge() in backend/app/custom.py. Your own logic goes there.",
    placeholder: "Type your input...",
  },
];
