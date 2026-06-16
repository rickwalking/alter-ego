/**
 * Re-export shim (AE-0140). `NeonBlogPostCard` is a business component owned by
 * the `publishing` bounded context; its canonical home is `@/modules/publishing`.
 * This shim keeps the legacy `@/components/organisms/neon-blog-post-card` path
 * resolving for existing importers during the Phase 7 migration window
 * (removal deferred to Phase 8). Import new code from `@/modules/publishing`.
 */
export {
  NeonBlogPostCard,
  type NeonBlogPostCardComponentProps,
} from "@/modules/publishing/blog/components/listing/neon-blog-post-card";
