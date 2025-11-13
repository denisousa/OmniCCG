import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format time strings like "[2025-11-11 ...] ... took 32.903s" to "32 seconds"
export function formatTime(timeStr: string) {
  if (!timeStr) return timeStr;
  // match the number before optional decimal and trailing 's'
  const m = timeStr.match(/(\d+)(?:\.\d+)?s/);
  if (m) return `${m[1]} seconds`;
  // fallback: replace standalone 's' with 'seconds'
  return timeStr.replace(/\bs\b/, "seconds");
}
