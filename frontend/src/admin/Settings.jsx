export default function Settings() {
  return (
    <div className="max-w-3xl mx-auto h-full overflow-y-auto pb-10">
      <h2 className="font-sans font-bold text-[24px] text-text-primary mb-2">System Settings</h2>
      <p className="text-[13px] text-text-secondary bg-[#fef3c7] border-[1.5px] border-[#fde68a] text-[#92400e] rounded-lg px-4 py-3 mb-6">
        Read-only preview — the settings backend arrives in Phase 2. Values shown are the current system defaults.
      </p>

      <div className="space-y-6">
        {/* General Settings */}
        <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-6 shadow-sm">
          <h3 className="font-sans font-bold text-[16px] text-text-primary mb-4 border-b-[1.5px] border-brand-border pb-2">General Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Company Name</label>
              <input disabled type="text" defaultValue="Everfresh Poultry" className="w-full max-w-md h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">PAN/VAT Number</label>
              <input disabled type="text" defaultValue="123456789" className="w-full max-w-md h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none" />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Default Date System</label>
              <select disabled className="w-full max-w-md h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                <option>Bikram Sambat (BS)</option>
                <option>Gregorian (AD)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Financial Settings */}
        <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-6 shadow-sm">
          <h3 className="font-sans font-bold text-[16px] text-text-primary mb-4 border-b-[1.5px] border-brand-border pb-2">Financial Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Standard VAT Rate (%)</label>
              <input disabled type="number" defaultValue="13" className="w-full max-w-[150px] h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none" />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Currency Symbol</label>
              <input disabled type="text" defaultValue="Rs" className="w-full max-w-[150px] h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
            </div>
          </div>
        </div>

        {/* CBMS Integration */}
        <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-6 shadow-sm">
          <h3 className="font-sans font-bold text-[16px] text-text-primary mb-4 border-b-[1.5px] border-brand-border pb-2">CBMS Integration (IRD)</h3>
          <div className="space-y-4">
            <div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input disabled type="checkbox" defaultChecked className="w-4 h-4 text-brand-primary focus:ring-brand-primary border-brand-border rounded" />
                <span className="text-[14px] text-text-primary font-medium">Enable real-time CBMS syncing</span>
              </label>
              <p className="text-[12px] text-text-secondary mt-1 ml-6">Invoices will be automatically transmitted to IRD upon generation.</p>
            </div>
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">API Base URL</label>
              <input disabled type="text" defaultValue="https://cbms.ird.gov.np/api" className="w-full max-w-md h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none" />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">API Credentials (Username / Password)</label>
              <div className="flex gap-2 max-w-md">
                <input disabled type="text" defaultValue="everfresh_api" className="w-1/2 h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none" />
                <input disabled type="password" defaultValue="********" className="w-1/2 h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none" />
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
