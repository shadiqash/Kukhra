# Import rule — enforced by convention, not Django machinery:
#
#   core depends on NOTHING outside Django itself.
#   All other apps may import from core's public surface (core.models, core.utils.*).
#   No app imports from a sibling app.
#   No app imports upward (i.e. nothing in apps/ touches config/).
#   Dependency direction: core ← everything else. Shared logic belongs in core.
