import csv
import ctypes
import heapq
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional


ProgressCallback = Optional[Callable[[dict], None]]


@dataclass
class ScanResult:
    drive: str
    output_csv: str
    files_scanned: int
    directories_scanned: int
    elapsed_seconds: float
    top_files: List[dict]


def get_available_drives() -> List[str]:
    """Return currently available Windows drive letters like ['C:\\', 'D:\\']."""
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    drives = []
    for index in range(26):
        if bitmask & (1 << index):
            drives.append(f"{chr(65 + index)}:\\")
    return drives


def format_size(size_bytes: int) -> str:
    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.2f} KB"
    size_mb = size_kb / 1024
    if size_mb < 1024:
        return f"{size_mb:.2f} MB"
    size_gb = size_mb / 1024
    return f"{size_gb:.2f} GB"


def export_top_files_csv(top_files: Iterable[dict], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "rank",
                "file_name",
                "size_bytes",
                "size_readable",
                "extension",
                "full_path",
            ]
        )
        for index, item in enumerate(top_files, start=1):
            writer.writerow(
                [
                    index,
                    item["file_name"],
                    item["size_bytes"],
                    item["size_readable"],
                    item["extension"],
                    item["full_path"],
                ]
            )


def delete_files(file_paths: Iterable[str]) -> dict:
    deleted = []
    failed = []

    for file_path in file_paths:
        try:
            os.remove(file_path)
            deleted.append(file_path)
        except (PermissionError, FileNotFoundError, OSError) as exc:
            failed.append({"path": file_path, "reason": str(exc)})

    return {"deleted": deleted, "failed": failed}


def scan_drive(
    drive: str,
    output_csv: str,
    top_n: int = 100,
    progress_callback: ProgressCallback = None,
    update_interval: float = 0.5,
) -> ScanResult:
    """
    Scan every file under the given drive, stream rows to CSV, and keep only the
    largest top_n files in memory to stay safe on very large file systems.
    """
    normalized_drive = str(Path(drive))
    files_scanned = 0
    directories_scanned = 0
    largest_files = []
    start_time = time.time()
    last_update = 0.0

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)

    with open(output_csv, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "file_name",
                "size_bytes",
                "size_readable",
                "extension",
                "full_path",
            ]
        )

        stack = [normalized_drive]
        while stack:
            current_dir = stack.pop()

            try:
                with os.scandir(current_dir) as entries:
                    directories_scanned += 1
                    for entry in entries:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                                continue

                            if not entry.is_file(follow_symlinks=False):
                                continue

                            stat = entry.stat(follow_symlinks=False)
                            extension = Path(entry.name).suffix.lower() or "(no extension)"
                            file_info = {
                                "file_name": entry.name,
                                "size_bytes": stat.st_size,
                                "size_readable": format_size(stat.st_size),
                                "extension": extension,
                                "full_path": entry.path,
                            }

                            writer.writerow(
                                [
                                    file_info["file_name"],
                                    file_info["size_bytes"],
                                    file_info["size_readable"],
                                    file_info["extension"],
                                    file_info["full_path"],
                                ]
                            )
                            files_scanned += 1

                            heap_item = (
                                file_info["size_bytes"],
                                file_info["full_path"],
                                file_info,
                            )
                            if len(largest_files) < top_n:
                                heapq.heappush(largest_files, heap_item)
                            elif heap_item[:2] > largest_files[0][:2]:
                                heapq.heapreplace(largest_files, heap_item)

                        except (PermissionError, FileNotFoundError, OSError):
                            continue
            except (PermissionError, FileNotFoundError, OSError):
                continue

            now = time.time()
            if progress_callback and now - last_update >= update_interval:
                progress_callback(
                    {
                        "current_dir": current_dir,
                        "files_scanned": files_scanned,
                        "directories_scanned": directories_scanned,
                        "elapsed_seconds": now - start_time,
                    }
                )
                last_update = now

    top_files = [
        item[2]
        for item in sorted(
            largest_files,
            key=lambda value: (value[0], value[1]),
            reverse=True,
        )
    ]

    if progress_callback:
        progress_callback(
            {
                "current_dir": normalized_drive,
                "files_scanned": files_scanned,
                "directories_scanned": directories_scanned,
                "elapsed_seconds": time.time() - start_time,
                "finished": True,
            }
        )

    return ScanResult(
        drive=normalized_drive,
        output_csv=output_csv,
        files_scanned=files_scanned,
        directories_scanned=directories_scanned,
        elapsed_seconds=time.time() - start_time,
        top_files=top_files,
    )
