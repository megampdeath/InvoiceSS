export function money(value?: string | number | null, currency = "EUR") {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  const amount = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(amount)) {
    return String(value);
  }
  return new Intl.NumberFormat("en", { style: "currency", currency }).format(amount);
}

export function shortDate(value?: string | null) {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

export function percent(value?: string | number | null) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  const number = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(number)) {
    return "-";
  }
  return `${Math.round(number * 100)}%`;
}
