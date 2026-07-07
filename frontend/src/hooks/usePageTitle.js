import { useEffect } from 'react'

/** Sets the browser tab title, restoring the app default on unmount. */
export function usePageTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} · Everfresh` : 'Everfresh POS'
    return () => {
      document.title = 'Everfresh POS'
    }
  }, [title])
}
