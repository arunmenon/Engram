cd /Users/arunmenon/MemoryRSI-Signals/work/executor-engram/harness
export HF_TOKEN=$(cat ~/.cache/huggingface/token)
for B in B1 B2; do
  CG_LLM_MODEL_ID="huggingface/google/gemma-4-31B-it" CG_LLM_MAX_TOKENS=16384 CG_LLM_TIMEOUT_SECONDS=600 PYTHONPATH=. ~/projects/Engram/.venv/bin/python -m gate_eval.locomo_extract --locomo /Users/arunmenon/MemoryRSI-Signals/work/datasets/frozen/SEATSWAP-LOCOMO-PDLC/locomo/locomo10.json --out ../runs/E-20260928-20-r2-20260929T052655Z/builds/$B --sessions-file ../runs/E-20260928-20-r2-20260929T052655Z/builds/sessions_A1_ok.txt --concurrency 8 --drop-params > ../runs/E-20260928-20-r2-20260929T052655Z/builds/$B.log 2>&1
done
