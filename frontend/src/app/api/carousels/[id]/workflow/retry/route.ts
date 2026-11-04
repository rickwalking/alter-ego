import { NextRequest, NextResponse } from "next/server";
import {
  proxyWorkflowAction,
  proxyWorkflowRead,
  WORKFLOW_ACTIONS,
} from "../_lib/proxy-workflow-action";

export function GET(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  return proxyWorkflowRead(request, context, WORKFLOW_ACTIONS.RETRY);
}

export function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  return proxyWorkflowAction(request, context, WORKFLOW_ACTIONS.RETRY);
}
