# On-Device Quantized LLM Inference

This directory contains research notes and benchmark scripts for evaluating quantized large language models (LLMs) on-device.

## Quantization Techniques

- **8-bit Quantization (INT8):** Reduces model weights to 8-bit integers, typically with minimal quality loss. Supported by frameworks like Hugging Face Transformers + `bitsandbytes`.
- **4-bit Quantization (INT4):** Further reduces memory footprint. Techniques like GPTQ (Post-Training Quantization for Generative LLMs) enable production-quality 4-bit quantization.
- **Mixed Precision (FP16/BF16):** Uses half-precision floats to accelerate computation, commonly on GPUs; useful on-device GPUs (e.g., mobile GPUs).
- **Quantized Llama.cpp (GGUF):** Standalone C++ implementation (`llama.cpp`) with support for Q4_0, Q4_1, Q5_X quantization formats for efficient CPU inference.

## Benchmarks

- **Text Generation:** `benchmark_text.py` measures tokens-per-second (throughput) and time per request for a quantized causal LM.
- **Audio Transcription:** `benchmark_audio.py` measures real-time factor and end-to-end latency using Whisper small model on CPU.

## Usage

Ensure Python dependencies are installed:

```bash
pip install -r requirements.txt
```

Run text benchmark:

```bash
python benchmarks/benchmark_text.py --model gpt2 --prompt "The quick brown fox" --steps 50
```

Run audio benchmark (replace `audio.wav` with your file):

```bash
python benchmarks/benchmark_audio.py --model small --audio_path audio.wav
```
