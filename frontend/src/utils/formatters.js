import NepaliDate from 'nepali-date-converter';

// Prices are always integer paisa
export const formatMoney = (paisa) => {
  const rupees = paisa / 100;
  return `Rs. ${rupees.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const formatWeight = (kg) => {
  return `${kg.toFixed(3)} kg`;
};

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
