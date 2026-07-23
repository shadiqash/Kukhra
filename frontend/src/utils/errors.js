// Extracts a human-readable message from an axios/DRF error.
// DRF error bodies come in several shapes:
//   {"detail": "..."}                          — permission / generic errors
//   {"counter": ["..."], "qty_kg": ["..."]}    — field validation errors
//   {"non_field_errors": ["..."]}              — object-level validation errors
//   ["..."]                                    — bare list
export function apiErrorMessage(err, fallback) {
  const data = err?.response?.data;
  if (!data) {
    if (err?.request && !err?.response) return 'Cannot reach the server. Check your connection.';
    return fallback;
  }
  if (typeof data === 'string') return fallback; // HTML error page — not user-presentable
  if (typeof data.detail === 'string') return data.detail;

  const firstMessage = (value) => {
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) return firstMessage(value[0]);
    if (value && typeof value === 'object') return firstMessage(Object.values(value)[0]);
    return null;
  };
  return firstMessage(data) ?? fallback;
}
