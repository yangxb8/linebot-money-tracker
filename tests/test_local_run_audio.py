"""Argparse smoke for local_run --audio."""

from __future__ import annotations

from local_run import _build_parser


def test_local_run_accepts_audio_flag():
    parser = _build_parser()
    args = parser.parse_args(["--audio", "clip.m4a", "--audio-duration-ms", "12000"])
    assert args.audio == "clip.m4a"
    assert args.audio_duration_ms == 12000
