/** Tracks and toggles light/dark theme, persisting the choice and defaulting to OS preference. */
import { useEffect, useState } from 'react'

const STORAGE_KEY = 'everfresh-theme'

function getInitialIsDark() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark' || stored === 'light') return stored === 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function useTheme() {
  const [isDark, setIsDark] = useState(getInitialIsDark)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
    localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light')
  }, [isDark])

  const toggleTheme = () => setIsDark((prev) => !prev)

  return { isDark, toggleTheme }
}
