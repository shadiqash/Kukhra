/**
 * Reusable hook for GET API calls with loading/error/data states.
 * Automatically re-fetches when `params` changes (shallow-compares via JSON).
 *
 * Usage:
 *   const { data, loading, error, refetch } = useApi(getProducts, { is_active: true })
 *   data is always the `results` array (handles paginated or plain responses)
 */
import { useCallback, useEffect, useRef, useState } from 'react'

export function useApi(apiFn, params) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const paramsRef = useRef(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiFn(params)
      // Handle both paginated { results: [...] } and plain array responses
      const raw = res.data
      setData(Array.isArray(raw) ? raw : (raw.results ?? []))
    } catch (e) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Request failed')
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiFn, JSON.stringify(params)])

  useEffect(() => {
    const serialized = JSON.stringify(params)
    if (paramsRef.current === serialized) return
    paramsRef.current = serialized
    fetch()
  }, [fetch, params])

  return { data, loading, error, refetch: fetch }
}
