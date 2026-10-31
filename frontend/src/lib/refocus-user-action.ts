import { MAIN_CONTENT_ID } from "@/constants/a11y";
import { USER_ACTION_ATTRIBUTE } from "@/constants/admin-users";

/** The value of `USER_ACTION_ATTRIBUTE` for one action of one user. */
export function userActionKey(action: string, userId: string): string {
  return `${action}:${userId}`;
}

function focusIsLost(): boolean {
  const active = document.activeElement;
  return active === null || active === document.body || !active.isConnected;
}

/**
 * After a dialog closes, put focus back on the same action of the same user
 * when the button that opened it is gone (the list swapped between table and
 * cards while the dialog was open), else on the main content. Runs after the
 * dialog's own focus restore, and does nothing when that one worked.
 */
export function refocusUserAction(action: string, userId: string): void {
  window.setTimeout(() => {
    if (!focusIsLost()) {
      return;
    }
    const selector = `[${USER_ACTION_ATTRIBUTE}="${userActionKey(action, userId)}"]`;
    const target =
      document.querySelector<HTMLElement>(selector) ??
      document.getElementById(MAIN_CONTENT_ID);
    target?.focus();
  }, 0);
}
