#!/usr/bin/env python3
"""
Benchmark quantized causal language model inference (8-bit) using HuggingFace Transformers + bitsandbytes.
"""
import argparse
import time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


def main():
    parser = argparse.ArgumentParser(description="Benchmark quantized text generation performance.")
    parser.add_argument("--model", type=str, default="gpt2", help="Model identifier (e.g., gpt2, EleutherAI/gpt-j-6B).")
    parser.add_argument("--prompt", type=str, default="Hello world", help="Text prompt to start generation.")
    parser.add_argument("--steps", type=int, default=50, help="Number of new tokens to generate for benchmark.")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading {args.model} in 8-bit quantized mode on {device}...")
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        device_map="auto" if torch.cuda.is_available() else None,
        load_in_8bit=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    gen = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        device=0 if torch.cuda.is_available() else -1,
    )

    # Warm-up
    print("Warming up...")
    _ = gen(args.prompt, max_new_tokens=10)

    # Benchmark
    print(f"Generating {args.steps} tokens...")
    start = time.time()
    output = gen(args.prompt, max_new_tokens=args.steps)
    elapsed = time.time() - start
    tps = args.steps / elapsed if elapsed > 0 else float("inf")

    print(f"\nElapsed time: {elapsed:.2f}s")
    print(f"Throughput: {tps:.2f} tokens/s")
    print(f"Result sample: {output[0]['generated_text']}")


if __name__ == "__main__":
    main()
