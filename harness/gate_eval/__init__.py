"""T4 experiment harness: naming audit (E-20260928-06-r2) and shared utilities.

Standard library only, so the pinned harness commit runs on any host without
package installs. Nothing here calls a model unless a TypeSafe key is present
in the environment and the caller passes an explicit call budget.
"""
