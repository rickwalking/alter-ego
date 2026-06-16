import { CREATE_TEMPLATES } from "@/constants/create";

export function findTemplateIndex(strategy: string | null | undefined): number {
  if (!strategy) return 0;
  return CREATE_TEMPLATES.findIndex((t) => t.strategy === strategy);
}
