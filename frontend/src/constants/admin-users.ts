export const USER_FILTER_ROLE_ALL = "all";

export const USER_FILTER_ROLE_ADMIN = "admin";

export const USER_FILTER_ROLE_EDITOR = "editor";

export const USER_FILTER_STATUS_ALL = "all";

export const USER_FILTER_STATUS_ACTIVE = "active";

export const USER_FILTER_STATUS_INACTIVE = "inactive";

export const USER_FULL_NAME_MAX_LENGTH = 255;

/** The request field of the name, as it appears in a 422 `loc`. */
export const USER_FULL_NAME_FIELD = "full_name";

/** The request field of the email, as it appears in a 422 `loc`. */
export const USER_EMAIL_FIELD = "email";

/** The request field of the password, as it appears in a 422 `loc`. */
export const USER_PASSWORD_FIELD = "password";

/** Fewest characters the API accepts for a typed password (its MIN_PASSWORD_LENGTH). */
export const USER_PASSWORD_MIN_LENGTH = 12;

/** Stable `code` values the admin user API sends next to its English `detail`. */
export const ADMIN_USER_ERROR_CODES = {
  EMAIL_EXISTS: "user_email_exists",
  LAST_ADMIN: "last_admin",
  SELF_DELETE: "self_delete",
} as const;

/** Below this width the user list renders as stacked cards instead of a table. */
export const USER_CARDS_MEDIA_QUERY = "(max-width: 767px)";

/** At least 44 x 44 px, the WCAG 2.5.5 touch target size. */
export const TOUCH_TARGET_CLASS = "min-h-11 min-w-11";

/** Marks a row action button with `<action>:<user id>`, to find it again after a re-render. */
export const USER_ACTION_ATTRIBUTE = "data-user-action";

/** The row actions, as written in `USER_ACTION_ATTRIBUTE`. */
export const USER_ACTIONS = {
  EDIT: "edit",
  RESET: "reset",
  DELETE: "delete",
} as const;
