import { z } from "zod";
import { API_ENDPOINTS } from "@/constants/api";
import {
  carouselBlogI18nResponseSchema,
  carouselBlogWithDesignResponseSchema,
  carouselDesignResponseSchema,
  carouselProjectListResponseSchema,
} from "@/schemas/carousel";

const DEFAULT_BASE_URL = "http://localhost:8000";

function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_BASE_URL;
}

async function validatedFetch<T>(
  url: string,
  schema: z.ZodSchema<T>,
  options?: { revalidate?: number }
): Promise<T | null> {
  const baseUrl = getBaseUrl();

  try {
    const res = await fetch(`${baseUrl}${url}`, {
      next: options?.revalidate ? { revalidate: options.revalidate } : undefined,
    });

    if (!res.ok) {
      return null;
    }

    const json: unknown = await res.json();
    const result = schema.safeParse(json);

    if (!result.success) {
      console.error("Server fetch validation failed:", result.error.issues);
      return null;
    }

    return result.data;
  } catch {
    return null;
  }
}

export async function fetchCompletedProjects(
  limit: number = 20
): Promise<z.infer<typeof carouselProjectListResponseSchema>> {
  const result = await validatedFetch(
    `${API_ENDPOINTS.CAROUSELS}?status=completed&limit=${limit}`,
    carouselProjectListResponseSchema,
    { revalidate: 3600 }
  );

  return result ?? { items: [], total: 0, limit, offset: 0 };
}

export async function fetchBlogWithDesign(
  id: string,
  lang: string = "pt"
): Promise<{
  blog: z.infer<typeof carouselBlogI18nResponseSchema>;
  design: z.infer<typeof carouselDesignResponseSchema>;
} | null> {
  const [blog, design] = await Promise.all([
    validatedFetch(
      API_ENDPOINTS.CAROUSEL_BLOG_LANG(id, lang),
      carouselBlogI18nResponseSchema,
      { revalidate: 3600 }
    ),
    validatedFetch(
      API_ENDPOINTS.CAROUSEL_DESIGN(id),
      carouselDesignResponseSchema,
      { revalidate: 3600 }
    ),
  ]);

  if (!blog || !design) {
    return null;
  }

  return { blog, design };
}

export async function fetchBlogWithDesignCombined(
  id: string,
  lang: string = "pt"
): Promise<z.infer<typeof carouselBlogWithDesignResponseSchema> | null> {
  return validatedFetch(
    `${API_ENDPOINTS.CAROUSEL_BLOG_LANG(id, lang)}?include_design=true`,
    carouselBlogWithDesignResponseSchema,
    { revalidate: 3600 }
  );
}
