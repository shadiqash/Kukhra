import { ClipboardList } from 'lucide-react';
import { getTodayBS } from '../utils/formatters';
import { useApi } from '../hooks/useApi';
import { getLots } from '../api';

export default function FlockLog() {
  const { data: lots } = useApi(getLots, { status: 'active' });
  const activeLot = lots[0] ?? null;

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-4 shadow-sm flex items-center justify-between">
        <div>
          <h2 className="font-sans font-bold text-[16px] text-text-primary">Current Active Lot</h2>
          <p className="font-mono text-brand-primary text-[14px]">{activeLot ? activeLot.code : 'None active'}</p>
        </div>
        {activeLot && (
          <div className="text-right">
            <p className="text-[12px] text-text-secondary">Live Weight</p>
            <p className="font-mono text-[16px] font-bold text-text-primary">{parseFloat(activeLot.live_weight_kg ?? 0).toFixed(1)} kg</p>
          </div>
        )}
      </div>

      <div className="flex justify-between items-center px-1">
        <h3 className="font-sans font-bold text-[15px] text-text-primary">Today's Log ({getTodayBS()})</h3>
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-5 shadow-sm flex-1 flex flex-col items-center justify-center text-text-secondary">
        <ClipboardList size={32} className="mb-3 opacity-40" />
        <p className="text-[14px]">Flock logging (feed, mortality, medication) is coming in Phase 2.</p>
        <p className="text-[12px] mt-1 opacity-60">Until then, record observations in the paper register.</p>
      </div>
    </div>
  );
}
