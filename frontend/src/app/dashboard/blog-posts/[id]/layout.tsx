import { API_ENDPOINTS } from "@/constants/api";
import { ownerResourceLayout } from "@/lib/owner-resource";

/** An unknown or malformed blog post id answers the not-found page (HTTP 404). */
export default ownerResourceLayout(API_ENDPOINTS.BLOG_POST_BY_ID);
