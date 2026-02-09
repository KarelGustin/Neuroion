#!/usr/bin/env python3
"""
Benchmark audio transcription performance using OpenAI Whisper.
"""
import argparse
import time
import wave

import whisper


def main():
    parser = argparse.ArgumentParser(description="Benchmark Whisper transcription performance.")
    parser.add_argument("--model", type=str, default="small", help="Whisper model size (tiny, base, small, medium, large).")
    parser.add_argument("--audio_path", type=str, required=True, help="Path to input audio file (WAV/MP3/...).")
    args = parser.parse_args()

    print(f"Loading Whisper '{args.model}' model...")
    model = whisper.load_model(args.model)

    # Calculate audio duration
    try:
        with wave.open(args.audio_path, 'rb') as wf:
            duration = wf.getnframes() / wf.getframerate()
    except Exception:
        duration = None

    # Warm-up: process a small segment (first 1 second) if possible
    print("Warming up...")
    _ = model.transcribe(args.audio_path, fp16=False, verbose=False)

    # Benchmark transcription
    print("Transcribing full audio...")
    start = time.time()
    result = model.transcribe(args.audio_path, fp16=False, verbose=False)
    elapsed = time.time() - start

    # Compute real-time factor (RTF)
    if duration:
        rtf = elapsed / duration if duration > 0 else float('inf')
    else:
        rtf = None

    print(f"\nElapsed time: {elapsed:.2f}s")
    if duration:
        print(f"Audio duration: {duration:.2f}s")
        print(f"Real-Time Factor (RTF): {rtf:.2f} (elapsed/duration)")
    print(f"Transcribed text sample: {result['text']}")


if __name__ == "__main__":
    main()
