import { NeonSkeleton } from "@/components/atoms/neon-skeleton";
import { DASHBOARD_CHAT_BG_DEEP } from "@/features/dashboard/chat/constants";

export default function ChatLoading() {
  return (
    <div
      className="flex flex-col min-h-screen"
      style={{ background: DASHBOARD_CHAT_BG_DEEP }}
    >
      <NeonSkeleton className="h-14 w-full rounded-none" />
      <div
        className="flex flex-1 gap-4 p-4"
        style={{ height: "calc(100vh - 56px)" }}
      >
        <div className="w-64 space-y-4">
          <NeonSkeleton className="h-10 w-full" />
          <div className="space-y-2">
            <NeonSkeleton className="h-12 w-full" />
            <NeonSkeleton className="h-12 w-full" />
            <NeonSkeleton className="h-12 w-full" />
            <NeonSkeleton className="h-12 w-full" />
          </div>
        </div>
        <div className="flex flex-1 flex-col gap-4">
          <div className="flex-1 space-y-4">
            <div className="flex gap-4">
              <NeonSkeleton className="h-10 w-10 rounded-full" />
              <NeonSkeleton className="h-20 flex-1" />
            </div>
            <div className="flex gap-4">
              <NeonSkeleton className="h-10 w-10 rounded-full" />
              <NeonSkeleton className="h-32 flex-1" />
            </div>
            <div className="flex gap-4">
              <NeonSkeleton className="h-10 w-10 rounded-full" />
              <NeonSkeleton className="h-20 flex-1" />
            </div>
          </div>
          <div className="flex gap-2">
            <NeonSkeleton className="h-20 flex-1" />
            <NeonSkeleton className="h-20 w-20" />
          </div>
        </div>
      </div>
    </div>
  );
}
