import type { Metadata } from "next";
import Workspace from "@/components/Workspace";
import { siteConfig } from "@/lib/config";

export const metadata: Metadata = { title: `Workspace · ${siteConfig.name}` };

export default function AppPage() {
  return <Workspace />;
}
