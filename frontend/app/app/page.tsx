import type { Metadata } from "next";
import BillDecoder from "@/components/BillDecoder";
import { siteConfig } from "@/lib/config";

export const metadata: Metadata = { title: `Decode a bill · ${siteConfig.name}` };

export default function AppPage() {
  return <BillDecoder />;
}
