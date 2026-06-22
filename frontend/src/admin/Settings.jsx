export default function Settings() {
  return (
    <div>
      <h1 className="text-xl font-bold text-gray-800 mb-6">Settings</h1>
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6 max-w-lg">
        <div>
          <h2 className="font-semibold text-gray-700 mb-1">VAT Registration</h2>
          <p className="text-sm text-gray-500">
            VAT registration status and per-product tax class are configurable from the Products screen.
            The default is <strong>exempt</strong>. Change tax_class to <em>taxable</em> to apply 13% VAT.
          </p>
        </div>
        <div>
          <h2 className="font-semibold text-gray-700 mb-1">CBMS / IRD Sync</h2>
          <p className="text-sm text-gray-500">
            Real IRD integration is Phase 2. The sync task currently logs and sets{' '}
            <code className="bg-gray-100 px-1 rounded">cbms_status</code> only.
          </p>
        </div>
        <div>
          <h2 className="font-semibold text-gray-700 mb-1">Cost Allocation</h2>
          <p className="text-sm text-gray-500">
            The method for splitting lot cost across output products (by weight vs. sales value) is pending
            management decision. <code className="bg-gray-100 px-1 rounded">accumulated_cost_paisa</code> is
            tracked but not yet allocated.
          </p>
        </div>
      </div>
    </div>
  )
}
