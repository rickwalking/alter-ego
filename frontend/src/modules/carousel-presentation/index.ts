/**
 * `carousel-presentation` — bounded-context public contract (AE-0139).
 *
 * Owns the carousel project / blog / design / slides query options
 * (preview / review / refinement read surface) migrated from the legacy
 * `features/carousel` folder. This barrel is the ONLY import surface for
 * cross-context and `app/` consumers; everything else under
 * `modules/carousel-presentation/**` is internal.
 *
 * See `src/modules/README.md` for the public-contract convention.
 */

export {
  carouselKeys,
  carouselListOptions,
  carouselProjectsOptions,
  carouselProjectOptions,
  carouselBlogOptions,
  carouselBlogWithDesignOptions,
  carouselDesignOptions,
  carouselSlidesOptions,
} from "./queries";
