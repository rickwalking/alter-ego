import { Skeleton } from "@/components/ui/skeleton";
import { Container } from "@/components/layout";

export default function ChatLoading() {
  return (
    <Container className="py-8">
      <div className="flex h-[calc(100vh-8rem)] gap-4">
        {/* Sidebar skeleton */}
        <div className="w-64 space-y-4">
          <Skeleton className="h-10 w-full" />
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        </div>

        {/* Chat area skeleton */}
        <div className="flex-1 flex flex-col gap-4">
          {/* Messages */}
          <div className="flex-1 space-y-4">
            <div className="flex gap-4">
              <Skeleton className="h-10 w-10 rounded-full" />
              <Skeleton className="h-20 flex-1" />
            </div>
            <div className="flex gap-4">
              <Skeleton className="h-10 w-10 rounded-full" />
              <Skeleton className="h-32 flex-1" />
            </div>
            <div className="flex gap-4">
              <Skeleton className="h-10 w-10 rounded-full" />
              <Skeleton className="h-20 flex-1" />
            </div>
          </div>

          {/* Input area */}
          <div className="flex gap-2">
            <Skeleton className="h-20 flex-1" />
            <Skeleton className="h-20 w-20" />
          </div>
        </div>
      </div>
    </Container>
  );
}
