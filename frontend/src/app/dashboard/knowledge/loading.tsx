import { Container } from "@/components/layout";
import { NeonSkeleton } from "@/components/atoms/neon-skeleton";

export default function KnowledgeLoading() {
  return (
    <Container className="py-8">
      {/* Header */}
      <div className="mb-8 space-y-2">
        <NeonSkeleton className="h-10 w-64" />
        <NeonSkeleton className="h-5 w-96" />
      </div>

      {/* Search and Add button */}
      <div className="flex items-center gap-4 mb-6">
        <NeonSkeleton className="h-10 flex-1" />
        <NeonSkeleton className="h-10 w-36" />
      </div>

      {/* Document grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="border rounded-lg p-6 space-y-4">
            <div className="flex items-start gap-3">
              <NeonSkeleton className="h-10 w-10 rounded-lg" />
              <div className="flex-1 space-y-2">
                <NeonSkeleton className="h-6 w-3/4" />
                <NeonSkeleton className="h-4 w-1/2" />
              </div>
            </div>
            <NeonSkeleton className="h-16 w-full" />
            <div className="flex gap-2">
              <NeonSkeleton className="h-6 w-16" />
              <NeonSkeleton className="h-6 w-16" />
            </div>
          </div>
        ))}
      </div>
    </Container>
  );
}
