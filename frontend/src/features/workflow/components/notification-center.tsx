"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Bell } from "lucide-react";
import { Badge, Button } from "@/components/ui";
import { useNotifications } from "@/features/workflow/hooks/use-notifications";

export function NotificationCenter() {
  const t = useTranslations("workflow.notifications");
  const { notifications, unreadCount, loading, markRead } = useNotifications();
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        aria-label={t("ariaLabel")}
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <Badge className="absolute -top-1 -right-1 h-5 min-w-5 px-1 text-xs">
            {unreadCount}
          </Badge>
        )}
      </Button>
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 rounded-md border bg-background shadow-lg z-50">
          <div className="border-b px-4 py-3 font-medium text-sm">
            {t("title")}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {loading && (
              <p className="p-4 text-sm text-muted-foreground">
                {t("loading")}
              </p>
            )}
            {!loading && notifications.length === 0 && (
              <p className="p-4 text-sm text-muted-foreground">{t("empty")}</p>
            )}
            {notifications.map((item) => (
              <button
                key={item.id}
                type="button"
                className="w-full text-left px-4 py-3 border-b hover:bg-muted/50 transition-colors"
                onClick={() => void markRead(item.id)}
              >
                <p className="text-sm font-medium">{item.title}</p>
                {item.body && (
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {item.body}
                  </p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  {new Date(item.created_at).toLocaleString()}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
