import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  cn,
  formatDate,
  formatRelativeTime,
  truncate,
  generateId,
  debounce,
  throttle,
} from "./utils";

describe("Utils Module", () => {
  describe("Given the cn utility function", () => {
    describe("When merging class names", () => {
      it("Then it should merge multiple class names into a single string", () => {
        expect(cn("foo", "bar")).toBe("foo bar");
      });

      it("Then it should handle conditional classes", () => {
        expect(cn("foo", true && "bar", false && "baz")).toBe("foo bar");
      });

      it("Then it should merge tailwind classes with proper precedence", () => {
        expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4");
      });

      it("Then it should handle null and undefined values", () => {
        expect(cn("foo", null, undefined, "bar")).toBe("foo bar");
      });

      it("Then it should handle empty strings", () => {
        expect(cn("foo", "", "bar")).toBe("foo bar");
      });

      it("Then it should handle arrays of classes", () => {
        expect(cn(["foo", "bar"], "baz")).toBe("foo bar baz");
      });

      it("Then it should handle objects for conditional classes", () => {
        expect(cn("foo", { bar: true, baz: false })).toBe("foo bar");
      });
    });
  });

  describe("Given the formatDate utility function", () => {
    describe("When formatting a date", () => {
      it("Then it should format a Date object correctly", () => {
        const date = new Date("2024-01-15T12:00:00Z");
        const result = formatDate(date);
        expect(result).toMatch(/^[A-Z][a-z]{2} \d{1,2}, \d{4}$/);
        expect(result).toContain("2024");
      });

      it("Then it should handle ISO string input", () => {
        const result = formatDate("2024-01-15T12:00:00Z");
        expect(result).toMatch(/^[A-Z][a-z]{2} \d{1,2}, \d{4}$/);
        expect(result).toContain("2024");
      });

      it("Then it should handle timestamp input", () => {
        const timestamp = new Date("2024-01-15T12:00:00Z").getTime();
        const result = formatDate(timestamp);
        expect(result).toMatch(/^[A-Z][a-z]{2} \d{1,2}, \d{4}$/);
        expect(result).toContain("2024");
      });

      it("Then it should handle different months correctly", () => {
        const jan = formatDate(new Date("2024-01-15"));
        const jun = formatDate(new Date("2024-06-15"));
        const dec = formatDate(new Date("2024-12-15"));

        expect(jan).toContain("Jan");
        expect(jun).toContain("Jun");
        expect(dec).toContain("Dec");
      });
    });
  });

  describe("Given the formatRelativeTime utility function", () => {
    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date("2024-01-15T12:00:00Z"));
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    describe("When formatting relative time", () => {
      it("Then it should return 'just now' for times less than 60 seconds ago", () => {
        const date = new Date("2024-01-15T11:59:30Z");
        expect(formatRelativeTime(date)).toBe("just now");
      });

      it("Then it should return minutes ago for times within the last hour", () => {
        const date = new Date("2024-01-15T11:55:00Z");
        expect(formatRelativeTime(date)).toBe("5m ago");
      });

      it("Then it should return hours ago for times within the last day", () => {
        const date = new Date("2024-01-15T08:00:00Z");
        expect(formatRelativeTime(date)).toBe("4h ago");
      });

      it("Then it should return days ago for times within the last week", () => {
        const date = new Date("2024-01-13T12:00:00Z");
        expect(formatRelativeTime(date)).toBe("2d ago");
      });

      it("Then it should return formatted date for times older than a week", () => {
        const date = new Date("2024-01-01T12:00:00Z");
        const result = formatRelativeTime(date);
        expect(result).toMatch(/^[A-Z][a-z]{2} \d{1,2}, \d{4}$/);
      });

      it("Then it should handle string input", () => {
        const date = "2024-01-15T11:55:00Z";
        expect(formatRelativeTime(date)).toBe("5m ago");
      });

      it("Then it should handle timestamp input", () => {
        const timestamp = new Date("2024-01-15T11:55:00Z").getTime();
        expect(formatRelativeTime(timestamp)).toBe("5m ago");
      });
    });
  });

  describe("Given the truncate utility function", () => {
    describe("When truncating a string", () => {
      it("Then it should return the original string if within limit", () => {
        expect(truncate("hello", 10)).toBe("hello");
      });

      it("Then it should truncate long strings with ellipsis", () => {
        expect(truncate("hello world", 8)).toBe("hello...");
      });

      it("Then it should handle exact limit without truncation", () => {
        expect(truncate("hello", 5)).toBe("hello");
      });

      it("Then it should handle very short max lengths", () => {
        expect(truncate("hello world", 4)).toBe("h...");
      });

      it("Then it should handle empty strings", () => {
        expect(truncate("", 10)).toBe("");
      });

      it("Then it should handle maxLength equal to 3", () => {
        expect(truncate("hello", 3)).toBe("...");
      });

      it("Then it should handle strings with special characters", () => {
        expect(truncate("hello @#$% world", 10)).toBe("hello @...");
      });
    });
  });

  describe("Given the generateId utility function", () => {
    describe("When generating an ID", () => {
      it("Then it should return a string", () => {
        const id = generateId();
        expect(typeof id).toBe("string");
      });

      it("Then it should return a unique ID on each call", () => {
        const id1 = generateId();
        const id2 = generateId();
        expect(id1).not.toBe(id2);
      });

      it("Then it should return a 7-character string", () => {
        const id = generateId();
        expect(id.length).toBe(7);
      });

      it("Then it should only contain alphanumeric characters", () => {
        const id = generateId();
        expect(id).toMatch(/^[a-z0-9]+$/);
      });
    });
  });

  describe("Given the debounce utility function", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    describe("When debouncing a function", () => {
      it("Then it should delay the function call", () => {
        const fn = vi.fn();
        const debouncedFn = debounce(fn, 100);

        debouncedFn();
        expect(fn).not.toHaveBeenCalled();

        vi.advanceTimersByTime(100);
        expect(fn).toHaveBeenCalledTimes(1);
      });

      it("Then it should reset the delay on subsequent calls", () => {
        const fn = vi.fn();
        const debouncedFn = debounce(fn, 100);

        debouncedFn();
        vi.advanceTimersByTime(50);
        debouncedFn();
        vi.advanceTimersByTime(50);
        debouncedFn();
        vi.advanceTimersByTime(100);

        expect(fn).toHaveBeenCalledTimes(1);
      });

      it("Then it should pass arguments to the debounced function", () => {
        const fn = vi.fn<(a: string, b: string) => void>(() => undefined) as unknown as (...args: unknown[]) => unknown;
        const debouncedFn = debounce(fn, 100);

        debouncedFn("arg1", "arg2");
        vi.advanceTimersByTime(100);

        expect(fn).toHaveBeenCalledWith("arg1", "arg2");
      });

      it("Then it should handle multiple arguments correctly", () => {
        const fn = vi.fn<(a: number, b: number, c: string) => string>((a: number, b: number, c: string) => a + b + c) as unknown as (...args: unknown[]) => unknown;
        const debouncedFn = debounce(fn, 100);

        debouncedFn(1, 2, "test");
        vi.advanceTimersByTime(100);

        expect(fn).toHaveBeenCalledWith(1, 2, "test");
      });
    });
  });

  describe("Given the throttle utility function", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    describe("When throttling a function", () => {
      it("Then it should call the function immediately on first invocation", () => {
        const fn = vi.fn();
        const throttledFn = throttle(fn, 100);

        throttledFn();
        expect(fn).toHaveBeenCalledTimes(1);
      });

      it("Then it should ignore calls within the throttle period", () => {
        const fn = vi.fn();
        const throttledFn = throttle(fn, 100);

        throttledFn();
        throttledFn();
        throttledFn();

        expect(fn).toHaveBeenCalledTimes(1);
      });

      it("Then it should allow calls after the throttle period", () => {
        const fn = vi.fn();
        const throttledFn = throttle(fn, 100);

        throttledFn();
        vi.advanceTimersByTime(100);
        throttledFn();

        expect(fn).toHaveBeenCalledTimes(2);
      });

      it("Then it should pass arguments to the throttled function", () => {
        const fn = vi.fn();
        const throttledFn = throttle(fn, 100);

        throttledFn("arg1", "arg2");

        expect(fn).toHaveBeenCalledWith("arg1", "arg2");
      });

      it("Then it should ignore intermediate calls during throttle period", () => {
        const fn = vi.fn();
        const throttledFn = throttle(fn, 100);

        throttledFn("first");
        vi.advanceTimersByTime(50);
        throttledFn("second");
        vi.advanceTimersByTime(60);
        throttledFn("third");

        expect(fn).toHaveBeenCalledTimes(2);
        expect(fn).toHaveBeenNthCalledWith(1, "first");
        expect(fn).toHaveBeenNthCalledWith(2, "third");
      });
    });
  });
});
