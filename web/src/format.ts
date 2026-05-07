export function shortDate(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

export function highlightHtml(value: string) {
  return value;
}

export function compactPath(value: string | null | undefined) {
  if (!value) return "";
  const parts = value.split("/").filter(Boolean);
  return parts[parts.length - 1] || value;
}

export function tailPath(value: string | null | undefined, count = 3) {
  if (!value) return "";
  const parts = value.split("/").filter(Boolean);
  if (parts.length <= count) return parts.join("/") || value;
  return parts.slice(-count).join("/");
}

export function fileName(value: string | null | undefined) {
  if (!value) return "";
  const parts = value.split("/");
  return parts[parts.length - 1] || value;
}

export function shortId(value: string | null | undefined) {
  if (!value) return "";
  return value.length > 8 ? value.slice(0, 8) : value;
}
