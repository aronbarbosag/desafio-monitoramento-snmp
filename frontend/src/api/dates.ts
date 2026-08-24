/**
 * Backend timestamps are naive UTC (no offset in the string). `new Date()`
 * on an offset-less datetime string parses as local time per the ECMAScript
 * spec, so we append "Z" when no offset is already present.
 */
export function parseApiDate(iso: string): Date {
  return new Date(/(Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`);
}

export function formatApiDate(iso: string): string {
  return parseApiDate(iso).toLocaleString("en-US");
}
