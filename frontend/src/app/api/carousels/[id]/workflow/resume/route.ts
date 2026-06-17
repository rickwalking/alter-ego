import { NextRequest, NextResponse } from "next/server";
import {
  proxyWorkflowAction,
  WORKFLOW_ACTIONS,
} from "../_lib/proxy-workflow-action";

// Allow long-running LLM resume calls through the Next.js proxy.
// Next.js route segment config must be a statically-analyzable literal
// (it cannot reference an imported constant), so this 300s value stays inline.
export const maxDuration = 300;

export function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  return proxyWorkflowAction(request, context, WORKFLOW_ACTIONS.RESUME);
}
