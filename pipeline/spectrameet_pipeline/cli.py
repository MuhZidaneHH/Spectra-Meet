"""Jalankan pipeline dari terminal, tanpa web (dipakai juga oleh API sebagai proses terpisah).

    python -m spectrameet_pipeline.cli data/uji/rekaman.wav --job-id uji1
"""

import argparse
import sys
import time

from .errors import PipelineError
from .run import process
from .transcribe import Options


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="spectrameet_pipeline")
    ap.add_argument("audio", help="jalur file audio")
    ap.add_argument("--job-id", default=time.strftime("lokal-%Y%m%d-%H%M%S"))
    ap.add_argument("--language", default="id-en", choices=["id-en", "id", "en"])
    ap.add_argument("--speakers", default="auto", help="auto, 2, 3, 4, atau 5+")
    ap.add_argument("--resume", action="store_true",
                    help="lanjutkan job yang sama (--job-id): tahap yang hasilnya masih berlaku dilewati")
    args = ap.parse_args(argv)

    t0 = time.time()
    try:
        result = process(args.audio, Options(args.language, args.speakers), job_id=args.job_id, resume=args.resume)
    except KeyboardInterrupt:
        print("Dibatalkan.", file=sys.stderr)
        return 130
    except PipelineError as e:
        print(f"GAGAL di tahap {e.step} [{e.code}]: {e.message}", file=sys.stderr)
        if e.detail:
            print(e.detail, file=sys.stderr)
        return 1

    speakers = sorted({s.speaker for s in result.segments})
    print(f"Selesai {time.time() - t0:.1f} dtk | {len(result.segments)} segmen | pembicara: {', '.join(speakers) or '-'}")
    for s in result.segments:
        print(f"[{s.start:7.1f}-{s.end:7.1f}] {s.speaker}: {s.text}")
    print(f"\nRingkasan [{result.summary_status}]", end="")
    if result.summary_status == "ok":
        print(f"\n{result.summary}")
        for title, items in (("Keputusan", result.decisions), ("Pertanyaan terbuka", result.open_questions)):
            print(f"{title}: " + ("; ".join(items) if items else "-"))
        print("Tugas: " + ("; ".join(f"{t.description} ({t.owner or '?'}, {t.due or '-'})" for t in result.tasks) or "-"))
    else:
        print(f": {result.summary_error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
