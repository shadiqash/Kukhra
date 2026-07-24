import NepaliDate from 'nepali-date-converter';

// Prices are always integer paisa (Rule 3: money never touches float). Split the
// integer into rupees and paise with divmod and format each part on its own, rather
// than dividing into a float and hoping toLocaleString rounds it back.
export const rupeesFromPaisa = (paisa) => {
  const neg = paisa < 0;
  const abs = Math.abs(Math.trunc(paisa));
  const rupees = Math.floor(abs / 100);
  const paise = abs % 100;
  return `${neg ? '-' : ''}${rupees.toLocaleString('en-IN')}.${String(paise).padStart(2, '0')}`;
};

export const formatMoney = (paisa) => `Rs. ${rupeesFromPaisa(paisa)}`;

// Bare "113.50" rupee string for number-input min/placeholder values, still derived
// from integer paisa rather than a float division.
export const paisaToAmount = (paisa) => {
  const abs = Math.abs(Math.trunc(paisa));
  return `${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, '0')}`;
};

export const formatWeight = (kg) => {
  return `${kg.toFixed(3)} kg`;
};

// ── VAT (inclusive) ─────────────────────────────────────────────────────────
// Shelf prices already contain the 13% VAT, so it is EXTRACTED, never added:
//   base = floor(inclusive × 100 / 113);  vat = inclusive − base.
// Mirrors the backend compute_line_vat so the receipt and the invoice agree.
export const vatFromInclusive = (inclusivePaisa) =>
  inclusivePaisa - Math.floor((inclusivePaisa * 100) / 113);

// Total VAT contained within a set of cart/order lines (per-line, to match the
// backend which extracts per line then sums). Exempt lines contribute nothing.
export const vatForLines = (lines) =>
  lines
    .filter((l) => l.tax_class === 'taxable')
    .reduce((s, l) => s + vatFromInclusive(l.line_total_paisa), 0);

// ── BS date formatters ──────────────────────────────────────────────────────
const MONTHS_EN = [
  'Baisakh', 'Jestha', 'Ashadh', 'Shrawan', 'Bhadra', 'Ashwin',
  'Kartik', 'Mangsir', 'Poush', 'Magh', 'Falgun', 'Chaitra'
];

export const formatDateString = (dateObj) => {
  // Returns something like "09 Ashadh 2083"
  const nd = new NepaliDate(dateObj);
  const day = nd.getDate().toString().padStart(2, '0');
  const month = MONTHS_EN[nd.getMonth()];
  const year = nd.getYear();
  return `${day} ${month} ${year}`;
};

export const formatDateTimeString = (dateObj) => {
  const d = new Date(dateObj);
  const nd = new NepaliDate(d);
  const day = nd.getDate().toString().padStart(2, '0');
  const month = MONTHS_EN[nd.getMonth()];
  const year = nd.getYear();

  let hours = d.getHours();
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12;
  hours = hours ? hours : 12;
  const minutes = d.getMinutes().toString().padStart(2, '0');
  
  return `${day} ${month} ${year}, ${hours.toString().padStart(2, '0')}:${minutes} ${ampm}`;
};

export const getTodayBS = () => {
  return formatDateString(new Date());
};
