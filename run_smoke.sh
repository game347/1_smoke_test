#!/bin/bash
set -e

LOG_FILE="smoke_test.log"
VLLM_LOG="vllm.log"

echo "=== Smoke Test Started ===" | tee $LOG_FILE
echo "Time: $(date)" | tee -a $LOG_FILE
nvidia-smi 2>&1 | tee -a $LOG_FILE

source $HOME/miniconda3/etc/profile.d/conda.sh 2>/dev/null || \
    source $HOME/anaconda3/etc/profile.d/conda.sh 2>/dev/null
conda activate rag

if [ ! -d "data/sn_long/2015-04-11 - Burnley - Arsenal" ]; then
    echo "ERROR: Burnley data missing. Copy from DGX first." | tee -a $LOG_FILE
    exit 1
fi
if [ ! -d "$HOME/models/Qwen2.5-7B-Instruct-AWQ" ]; then
    echo "ERROR: Qwen2.5-7B-AWQ missing. Copy from DGX." | tee -a $LOG_FILE
    exit 1
fi
if [ ! -d "$HOME/models/Qwen3-VL-30B-A3B-Instruct" ]; then
    echo "ERROR: Qwen3-VL-30B missing. Copy from DGX." | tee -a $LOG_FILE
    exit 1
fi

vllm serve $HOME/models/Qwen2.5-7B-Instruct-AWQ \
    --port 8001 --quantization awq \
    --enable-auto-tool-choice --tool-call-parser hermes \
    --gpu-memory-utilization 0.20 --max-model-len 4096 \
    > $VLLM_LOG 2>&1 &
VLLM_PID=$!

echo "Waiting for vLLM..." | tee -a $LOG_FILE
for i in {1..120}; do
    if curl -s http://localhost:8001/v1/models > /dev/null 2>&1; then
        echo "vLLM ready after $((i*5))s" | tee -a $LOG_FILE
        break
    fi
    sleep 5
done

if ! curl -s http://localhost:8001/v1/models > /dev/null 2>&1; then
    echo "ERROR: vLLM did not start. See $VLLM_LOG" | tee -a $LOG_FILE
    kill $VLLM_PID 2>/dev/null
    exit 1
fi

echo "=== Running smoke test on Burnley ===" | tee -a $LOG_FILE
python experiments/level1_baseline.py --match "Burnley" 2>&1 | tee -a $LOG_FILE

kill $VLLM_PID 2>/dev/null

echo "" | tee -a $LOG_FILE
echo "=== Smoke Test Complete ===" | tee -a $LOG_FILE
echo "Time: $(date)" | tee -a $LOG_FILE
echo "Results:" | tee -a $LOG_FILE
cat experiments/results.json 2>&1 | tee -a $LOG_FILE
