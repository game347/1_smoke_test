# 1_smoke_test — Soccer EKG Pipeline Smoke Test

Quick test to confirm the pipeline runs end-to-end on ONE match.
~30-45 minutes on H100 80GB. Output: AI commentary + metrics.

## Prerequisites
- Linux server with SLURM
- 1× GPU with ≥40 GB memory (H100, A100 80GB)
- conda installed
- ~80 GB free disk (models + 1 match)

## Steps

### 1. Clone main project + this smoke repo
```bash
cd ~
git clone https://github.com/wer11002/real-time_KG-with-vlm
git clone https://github.com/<user>/1_smoke_test
2. Get data + models from DGX
Run on DGX:


cd ~/work/s2616011

# Code already in main repo — only need data + models
rsync -avhP --stats \
  --include='/sn_long/' \
  --include='/sn_long/2015-04-11 - Burnley - Arsenal/***' \
  --exclude='/sn_long/*' \
  --exclude='*' \
  real-time_KG-with-vlm/data/ \
  USER@FRIEND_SERVER:~/real-time_KG-with-vlm/data/

rsync -avhP --stats \
  models/Qwen2.5-7B-Instruct-AWQ/ \
  USER@FRIEND_SERVER:~/models/Qwen2.5-7B-Instruct-AWQ/
3. Set up conda env (one time)

cd ~/real-time_KG-with-vlm
conda env create -f environment.yml -n rag
conda activate rag
4. Copy the smoke test script and submit

cp ~/1_smoke_test/smoke_test.sh ~/real-time_KG-with-vlm/
cd ~/real-time_KG-with-vlm
sbatch smoke_test.sh
squeue -u $USER
5. Watch (optional)

tail -f logs/smoke-*.log
6. When done — send these back

# After job finishes:
cat experiments/results.json
cat logs/smoke-*.log | tail -100
Send me:

experiments/results.json
logs/smoke-<JOB_ID>.log
