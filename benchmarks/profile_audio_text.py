#!/usr/bin/env python3
"""
Profile end-to-end audio->text->LLM generation pipeline latency and throughput.
"""
import argparse
import time
import torch
import whisper
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


def main():
    parser = argparse.ArgumentParser(description="Profile audio->LLM pipeline: whisper + quantized LLM generation.")
    parser.add_argument("--audio_path", type=str, required=True, help="Input audio file path.")
    parser.add_argument("--whisper_model", type=str, default="small", help="Whisper model size.")
    parser.add_argument("--llm_model", type=str, default="gpt2", help="Causal LLM model identifier.")
    parser.add_argument("--prompt_template", type=str, default="Transcribe and summarize: {transcript}", help="Template for prompt to LLM.")
    parser.add_argument("--gen_steps", type=int, default=50, help="Number of tokens to generate.")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    t0 = time.time()
    print(f"Loading Whisper model '{args.whisper_model}'...")
    whisper_model = whisper.load_model(args.whisper_model)
    t1 = time.time()

    print(f"Transcribing audio '{args.audio_path}'...")
    result = whisper_model.transcribe(args.audio_path, fp16=False, verbose=False)
    transcript = result.get("text", "")
    t2 = time.time()

    print(f"Loading LLM model '{args.llm_model}' in 8-bit quantized mode...")
    llm = AutoModelForCausalLM.from_pretrained(
        args.llm_model,
        device_map="auto" if torch.cuda.is_available() else None,
        load_in_8bit=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.llm_model)
    llm_pipeline = pipeline(
        "text-generation", model=llm, tokenizer=tokenizer,
        device=0 if torch.cuda.is_available() else -1
    )
    t3 = time.time()

    prompt = args.prompt_template.format(transcript=transcript)
    print(f"Generating {args.gen_steps} tokens with LLM...")
    out = llm_pipeline(prompt, max_new_tokens=args.gen_steps)
    t4 = time.time()

    print("\n=== Timings ===")
    print(f"Whisper load: {t1-t0:.2f}s")
    print(f"Transcription: {t2-t1:.2f}s")
    print(f"LLM load: {t3-t2:.2f}s")
    print(f"Generation: {t4-t3:.2f}s")
    print(f"Total pipeline: {t4-t0:.2f}s")

    print("\n=== Output ===")
    print(f"Transcript: {transcript}")
    print(f"Generated: {out[0]['generated_text']}")

if __name__ == "__main__":
    main()
