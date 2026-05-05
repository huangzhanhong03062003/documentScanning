import queue
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from scanner_core import delete_files, export_top_files_csv, get_available_drives, scan_drive


class FileScannerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Windows File Scanner")
        self.root.geometry("920x620")

        self.drives = get_available_drives()
        self.progress_queue = queue.Queue()
        self.is_scanning = False
        self.current_top_files = []

        self._build_ui()
        self.root.after(200, self._poll_progress)

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        title = ttk.Label(container, text="Windows File Scanner", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w")

        description = ttk.Label(
            container,
            text="Choose a drive to scan. The tool exports all files to CSV and also exports the largest Top 100 files.",
        )
        description.pack(anchor="w", pady=(6, 16))

        top_bar = ttk.Frame(container)
        top_bar.pack(fill="x")

        ttk.Label(top_bar, text="Drive:").pack(side="left")
        self.drive_var = tk.StringVar(value=self.drives[0] if self.drives else "")
        self.drive_combo = ttk.Combobox(
            top_bar,
            textvariable=self.drive_var,
            values=self.drives,
            state="readonly",
            width=12,
        )
        self.drive_combo.pack(side="left", padx=(8, 12))

        self.scan_button = ttk.Button(top_bar, text="Start Scan", command=self.start_scan)
        self.scan_button.pack(side="left")

        self.delete_button = ttk.Button(top_bar, text="Delete Selected", command=self.delete_selected)
        self.delete_button.pack(side="left", padx=(8, 0))
        self.delete_button.config(state="disabled")

        self.progress = ttk.Progressbar(container, mode="indeterminate")
        self.progress.pack(fill="x", pady=(16, 8))

        self.status_var = tk.StringVar(value="Waiting to start.")
        ttk.Label(container, textvariable=self.status_var).pack(anchor="w")

        stats_frame = ttk.Frame(container)
        stats_frame.pack(fill="x", pady=(8, 12))
        self.files_var = tk.StringVar(value="Files scanned: 0")
        self.dirs_var = tk.StringVar(value="Directories scanned: 0")
        ttk.Label(stats_frame, textvariable=self.files_var).pack(side="left", padx=(0, 20))
        ttk.Label(stats_frame, textvariable=self.dirs_var).pack(side="left")

        columns = ("rank", "size", "name", "path")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", height=18)
        self.tree.heading("rank", text="Rank")
        self.tree.heading("size", text="Size")
        self.tree.heading("name", text="File Name")
        self.tree.heading("path", text="Full Path")
        self.tree.column("rank", width=60, anchor="center")
        self.tree.column("size", width=110, anchor="e")
        self.tree.column("name", width=220)
        self.tree.column("path", width=480)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def start_scan(self):
        if self.is_scanning:
            return

        drive = self.drive_var.get().strip()
        if not drive:
            messagebox.showwarning("Notice", "Please choose a drive first.")
            return

        self.is_scanning = True
        self.scan_button.config(state="disabled")
        self.progress.start(10)
        self.status_var.set(f"Scanning {drive}. Inaccessible folders will be skipped automatically.")
        self.files_var.set("Files scanned: 0")
        self.dirs_var.set("Directories scanned: 0")
        self.current_top_files = []
        self.delete_button.config(state="disabled")
        for item in self.tree.get_children():
            self.tree.delete(item)

        worker = threading.Thread(target=self._scan_in_background, args=(drive,), daemon=True)
        worker.start()

    def _scan_in_background(self, drive: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path.cwd() / "outputs"
        detail_csv = output_dir / f"scan_{drive[0]}_{timestamp}.csv"
        top_csv = output_dir / f"largest_100_{drive[0]}_{timestamp}.csv"

        def report(info):
            self.progress_queue.put(("progress", info))

        try:
            result = scan_drive(drive, str(detail_csv), progress_callback=report)
            export_top_files_csv(result.top_files, str(top_csv))
            self.progress_queue.put(("done", result, str(top_csv)))
        except Exception as exc:
            self.progress_queue.put(("error", str(exc)))

    def _poll_progress(self):
        try:
            while True:
                item = self.progress_queue.get_nowait()
                kind = item[0]

                if kind == "progress":
                    info = item[1]
                    self.files_var.set(f"Files scanned: {info['files_scanned']}")
                    self.dirs_var.set(f"Directories scanned: {info['directories_scanned']}")
                    self.status_var.set(
                        f"Current: {info['current_dir']} | Elapsed: {info['elapsed_seconds']:.1f}s"
                    )
                elif kind == "done":
                    result, top_csv = item[1], item[2]
                    self._show_result(result)
                    self.progress.stop()
                    self.scan_button.config(state="normal")
                    self.is_scanning = False
                    self.current_top_files = result.top_files
                    self.delete_button.config(state="normal" if result.top_files else "disabled")
                    self.status_var.set(
                        f"Scan completed. Details: {result.output_csv} | Top 100: {top_csv}"
                    )
                    messagebox.showinfo(
                        "Scan Completed",
                        f"Scanned {result.files_scanned} files.\n"
                        f"All files CSV: {result.output_csv}\n"
                        f"Top 100 CSV: {top_csv}",
                    )
                elif kind == "error":
                    self.progress.stop()
                    self.scan_button.config(state="normal")
                    self.is_scanning = False
                    self.status_var.set("Scan failed.")
                    messagebox.showerror("Error", item[1])
        except queue.Empty:
            pass

        self.root.after(200, self._poll_progress)

    def _show_result(self, result):
        for index, item in enumerate(result.top_files, start=1):
            self.tree.insert(
                "",
                "end",
                values=(index, item["size_readable"], item["file_name"], item["full_path"]),
            )

    def delete_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Notice", "Please select one or more files to delete.")
            return

        paths_to_delete = []
        preview_lines = []
        for tree_item in selected_items:
            values = self.tree.item(tree_item, "values")
            if not values:
                continue
            rank = int(values[0])
            file_info = self.current_top_files[rank - 1]
            paths_to_delete.append(file_info["full_path"])
            preview_lines.append(f"{rank}. {file_info['size_readable']} | {file_info['full_path']}")

        if not paths_to_delete:
            messagebox.showwarning("Notice", "No valid files were selected.")
            return

        confirmed = messagebox.askyesno(
            "Confirm Delete",
            "The selected files will be permanently deleted.\n\n"
            + "\n".join(preview_lines[:10])
            + ("\n..." if len(preview_lines) > 10 else ""),
        )
        if not confirmed:
            return

        summary = delete_files(paths_to_delete)
        deleted_paths = set(summary["deleted"])

        for tree_item in list(selected_items):
            values = self.tree.item(tree_item, "values")
            if values and values[3] in deleted_paths:
                self.tree.delete(tree_item)

        self.current_top_files = [
            item for item in self.current_top_files if item["full_path"] not in deleted_paths
        ]
        self._reload_tree()

        message = (
            f"Deleted files: {len(summary['deleted'])}\n"
            f"Failed deletions: {len(summary['failed'])}"
        )
        if summary["failed"]:
            failed_preview = "\n".join(
                f"{item['path']} | {item['reason']}" for item in summary["failed"][:5]
            )
            message += f"\n\nFailed examples:\n{failed_preview}"

        self.status_var.set(message.replace("\n", " | "))
        messagebox.showinfo("Cleanup Result", message)

    def _reload_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for index, item in enumerate(self.current_top_files, start=1):
            self.tree.insert(
                "",
                "end",
                values=(index, item["size_readable"], item["file_name"], item["full_path"]),
            )


def main():
    root = tk.Tk()
    app = FileScannerApp(root)
    if not app.drives:
        messagebox.showwarning("Notice", "No available drives were detected.")
    root.mainloop()


if __name__ == "__main__":
    main()
