"""E-20260928-12 setup only: MEMDEC-OD export, repository-level splits, soft targets.

No fine-tuning or model calls live here. Training (Qwen3.5 bases, od1 recipe)
needs a GPU host and model downloads that this package deliberately does not
perform; see harness/README.md.
"""
