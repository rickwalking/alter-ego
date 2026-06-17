/** Constants for the publish-page chat feature. */

/** Prefix for localStorage keys that store conversation IDs per project. */
export const PUBLISH_CHAT_STORAGE_KEY_PREFIX = "alter-ego:publish-conversation";

/** Build the localStorage key for a given project ID. */
export function PUBLISH_CHAT_STORAGE_KEY(projectId: string): string {
  return `${PUBLISH_CHAT_STORAGE_KEY_PREFIX}:${projectId}`;
}

/** Prefix for optimistic user message IDs. */
export const OPTIMISTIC_MESSAGE_ID_PREFIX = "opt-";

/** Prefix for stream-assigned message IDs. */
export const STREAM_MESSAGE_ID_PREFIX = "stream-";

/** Prefix for conversation titles on the publish page. */
export const CONVERSATION_TITLE_PREFIX = "Refine: ";

/** Metadata key that links a conversation to its carousel project. */
export const CONVERSATION_METADATA_PROJECT_ID = "project_id";

/** Metadata key identifying which agent owns the conversation. */
export const CONVERSATION_METADATA_AGENT_ORIGIN = "agent_origin";

/** Agent origin value for Alter-Ego personal chat. */
export const AGENT_ORIGIN_ALTER_EGO = "alter_ego";

/** Agent origin value for carousel workspace / publish chat. */
export const AGENT_ORIGIN_CAROUSEL = "carousel";

/** Query param for listing Alter-Ego-only conversations. */
export const CONVERSATION_ORIGIN_FILTER_ALTER_EGO = "alter_ego";

/** Tool name for carousel copy refinement. */
export const TOOL_REFINE_CAROUSEL_COPY = "refine_carousel_copy";
