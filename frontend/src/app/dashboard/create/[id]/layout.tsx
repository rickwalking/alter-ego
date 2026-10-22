import { API_ENDPOINTS } from "@/constants/api";
import { ownerResourceLayout } from "@/lib/owner-resource";

/** An unknown or malformed carousel id answers the not-found page (HTTP 404). */
export default ownerResourceLayout(API_ENDPOINTS.CAROUSEL_BY_ID);
