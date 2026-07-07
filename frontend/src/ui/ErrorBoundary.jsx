import { Component } from 'react'

/**
 * Last-resort catch for render errors so a crash in one screen never leaves
 * the operator staring at a blank page. Reload restores a clean state.
 */
export default class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Unhandled render error:', error, info)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="h-screen flex items-center justify-center bg-brand-surface font-sans p-4">
        <div className="bg-white rounded-xl border-[1.5px] border-brand-border shadow-md p-8 max-w-md text-center">
          <h1 className="text-[20px] font-bold text-text-primary mb-2">Something went wrong</h1>
          <p className="text-[14px] text-text-secondary mb-6">
            The screen hit an unexpected error. Your data is safe — reload to continue.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="h-11 px-6 bg-brand-primary text-white rounded-md font-semibold hover:bg-brand-primaryHover transition-colors"
          >
            Reload
          </button>
        </div>
      </div>
    )
  }
}
