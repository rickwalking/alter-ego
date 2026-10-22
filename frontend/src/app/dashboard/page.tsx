import type { Metadata } from "next";
import { pageMetadata } from "@/lib/page-metadata";
import { DashboardHome } from "./dashboard-home";

/** Page title for the dashboard overview. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("dashboard");
}

export default function DashboardPage(): React.ReactElement {
  return <DashboardHome />;
}
