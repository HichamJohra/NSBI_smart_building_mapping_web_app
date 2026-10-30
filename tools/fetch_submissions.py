"""Download the data contributions received by the web app, then delete them from the server storage.

Run on your own PC (not part of the web app). Each submission is an Excel file written by the
'Contribute data' page. The script
  1. downloads every submission to a local folder,
  2. checks that each download is complete (size + MD5 checksum against Cloud Storage),
  3. deletes the submission from the bucket (unless --keep),
  4. writes combined_submissions.xlsx: all submitted buildings in one sheet, with their submission id,
     ready for review before copying accepted rows into data/smart_buildings_dataset.xlsx.

From Google Cloud Storage (production):
    pip install -r tools/requirements-tools.txt          # once
    gcloud auth application-default login                # once, with your Google account
    python tools/fetch_submissions.py --bucket nsbi-submissions

From a local folder (development, when the app runs on your PC):
    python tools/fetch_submissions.py --local-dir submissions

Options:
    --dest DIR      where to save (default: downloaded_submissions/<date-time>)
    --keep          download only, do not delete anything
    --no-combine    do not write combined_submissions.xlsx
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _md5_b64(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return base64.b64encode(h.digest()).decode()


def fetch_from_bucket(bucket_name: str, dest: Path, keep: bool, prefix: str = "") -> list[Path]:
    try:
        from google.cloud import storage
    except ImportError:
        sys.exit("google-cloud-storage is missing: pip install -r tools/requirements-tools.txt")
    client = storage.Client()
    blobs = [b for b in client.list_blobs(bucket_name, prefix=prefix or None) if b.name.lower().endswith(".xlsx")]
    if not blobs:
        print(f"No submissions in gs://{bucket_name}/{prefix}")
        return []
    dest.mkdir(parents=True, exist_ok=True)
    saved = []
    for blob in blobs:
        target = dest / Path(blob.name).name
        blob.download_to_filename(target)
        ok = target.stat().st_size == blob.size and (blob.md5_hash is None or _md5_b64(target) == blob.md5_hash)
        if not ok:
            print(f"  ! {blob.name}: download incomplete, kept in the bucket")
            continue
        saved.append(target)
        if not keep:
            # delete only this exact version (protects a file re-written in the meantime)
            blob.delete(if_generation_match=blob.generation)
        print(f"  {'kept   ' if keep else 'fetched'} {blob.name}")
    return saved


def fetch_from_folder(folder: Path, dest: Path, keep: bool) -> list[Path]:
    files = sorted(p for p in folder.glob("*.xlsx") if not p.name.startswith("~$"))
    if not files:
        print(f"No submissions in {folder}")
        return []
    dest.mkdir(parents=True, exist_ok=True)
    saved = []
    for p in files:
        target = dest / p.name
        shutil.copy2(p, target)
        if _md5_b64(target) != _md5_b64(p):
            print(f"  ! {p.name}: copy incomplete, kept")
            continue
        saved.append(target)
        if not keep:
            p.unlink()
        print(f"  {'kept   ' if keep else 'fetched'} {p.name}")
    return saved


def combine(files: list[Path], dest: Path) -> Path | None:
    """All submitted buildings in one Excel sheet, first column = submission id."""
    import pandas as pd
    frames = []
    for f in files:
        try:
            b = pd.read_excel(f, sheet_name="buildings", dtype=object)
            info = pd.read_excel(f, sheet_name="submission_info", header=None, dtype=object)  # key | value rows
        except Exception as e:  # noqa: BLE001 – report and continue with the other files
            print(f"  ! {f.name}: cannot be read ({e})")
            continue
        meta = dict(zip(info.iloc[:, 0], info.iloc[:, 1])) if info.shape[1] >= 2 else {}
        if b is None or b.empty:
            continue
        b.insert(0, "submission_id", meta.get("submission_id", f.stem))
        b.insert(1, "received_utc", meta.get("received_utc", ""))
        b.insert(2, "channel", meta.get("channel", ""))
        b.insert(3, "submission_comment", meta.get("comment", ""))
        frames.append(b)
    if not frames:
        return None
    out = dest / "combined_submissions.xlsx"
    pd.concat(frames, ignore_index=True).to_excel(out, sheet_name="buildings", index=False)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Download (and delete) data contributions of the NSBI web app.")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--bucket", default=os.environ.get("NSBI_SUBMISSIONS_BUCKET"),
                     help="Cloud Storage bucket name (or env NSBI_SUBMISSIONS_BUCKET)")
    src.add_argument("--local-dir", type=Path, help="local submissions folder instead of a bucket")
    ap.add_argument("--prefix", default="", help="only objects whose name starts with this prefix")
    ap.add_argument("--dest", type=Path, default=None, help="destination folder")
    ap.add_argument("--keep", action="store_true", help="do not delete after downloading")
    ap.add_argument("--no-combine", action="store_true", help="do not write combined_submissions.xlsx")
    args = ap.parse_args()
    if not args.bucket and not args.local_dir:
        ap.error("give --bucket NAME (or set NSBI_SUBMISSIONS_BUCKET) or --local-dir FOLDER")

    dest = args.dest or ROOT / "downloaded_submissions" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"Destination: {dest}")
    files = (fetch_from_folder(args.local_dir, dest, args.keep) if args.local_dir
             else fetch_from_bucket(args.bucket, dest, args.keep, args.prefix))
    print(f"{len(files)} submission file(s) {'downloaded' if args.keep else 'downloaded and removed from the server'}.")
    if files and not args.no_combine:
        out = combine(files, dest)
        if out:
            print(f"Review file: {out}")


if __name__ == "__main__":
    main()
