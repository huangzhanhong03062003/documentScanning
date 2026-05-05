from datetime import datetime
from pathlib import Path

from scanner_core import delete_files, export_top_files_csv, get_available_drives, scan_drive


def choose_drive(drives):
    print("Available drives:")
    for index, drive in enumerate(drives, start=1):
        print(f"{index}. {drive}")

    while True:
        selected = input("Enter the drive number to scan: ").strip()
        if not selected.isdigit():
            print("Please enter a valid number.")
            continue

        selected_index = int(selected)
        if 1 <= selected_index <= len(drives):
            return drives[selected_index - 1]

        print("Number out of range. Please try again.")


def main():
    drives = get_available_drives()
    if not drives:
        print("No available drives were detected.")
        return

    selected_drive = choose_drive(drives)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path.cwd() / "outputs"
    detail_csv = output_dir / f"scan_{selected_drive[0]}_{timestamp}.csv"
    top_csv = output_dir / f"largest_100_{selected_drive[0]}_{timestamp}.csv"

    print(f"\nScanning drive: {selected_drive}")
    print(f"Detail CSV: {detail_csv}")
    print(f"Top 100 CSV: {top_csv}")
    print("Scanning has started. Inaccessible folders will be skipped automatically.\n")

    def show_progress(info):
        elapsed = info["elapsed_seconds"]
        print(
            "\rFiles scanned: {files} | Directories scanned: {dirs} | Current: {current} | Elapsed: {elapsed:.1f}s".format(
                files=info["files_scanned"],
                dirs=info["directories_scanned"],
                current=info["current_dir"][:60],
                elapsed=elapsed,
            ),
            end="",
            flush=True,
        )

    result = scan_drive(selected_drive, str(detail_csv), progress_callback=show_progress)
    export_top_files_csv(result.top_files, str(top_csv))

    print("\n\nScan completed.")
    print(f"Total files: {result.files_scanned}")
    print(f"Total directories: {result.directories_scanned}")
    print(f"Elapsed: {result.elapsed_seconds:.2f} seconds")
    print(f"All files CSV: {result.output_csv}")
    print(f"Top 100 CSV: {top_csv}")

    print("\nTop 10 largest files:")
    for index, item in enumerate(result.top_files[:10], start=1):
        print(
            f"{index:>2}. {item['size_readable']:>10} | {item['file_name']} | {item['full_path']}"
        )

    ask_cleanup(result.top_files)


def ask_cleanup(top_files):
    if not top_files:
        return

    print("\nTop 100 largest files:")
    for index, item in enumerate(top_files, start=1):
        print(f"{index:>3}. {item['size_readable']:>10} | {item['file_name']} | {item['full_path']}")

    answer = input("\nDo you want to delete selected files from the Top 100 list? (y/N): ").strip().lower()
    if answer not in {"y", "yes"}:
        return

    raw_selection = input(
        "Enter file numbers to delete, separated by commas (example: 1,3,5): "
    ).strip()
    if not raw_selection:
        print("No files selected. Cleanup cancelled.")
        return

    selected_indexes = []
    for part in raw_selection.split(","):
        part = part.strip()
        if not part.isdigit():
            print(f"Invalid selection ignored: {part}")
            continue

        index = int(part)
        if 1 <= index <= len(top_files):
            selected_indexes.append(index)
        else:
            print(f"Out-of-range selection ignored: {index}")

    selected_indexes = sorted(set(selected_indexes))
    if not selected_indexes:
        print("No valid files selected. Cleanup cancelled.")
        return

    print("\nFiles to be deleted:")
    selected_paths = []
    for index in selected_indexes:
        item = top_files[index - 1]
        selected_paths.append(item["full_path"])
        print(f"{index:>3}. {item['size_readable']:>10} | {item['full_path']}")

    confirm = input("\nType DELETE to confirm permanent deletion: ").strip()
    if confirm != "DELETE":
        print("Cleanup cancelled.")
        return

    summary = delete_files(selected_paths)
    print(f"\nDeleted files: {len(summary['deleted'])}")
    print(f"Failed deletions: {len(summary['failed'])}")
    for item in summary["failed"]:
        print(f"FAILED | {item['path']} | {item['reason']}")


if __name__ == "__main__":
    main()
