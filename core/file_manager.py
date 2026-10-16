"""
Advanced Local & Cloud File Manager for Vanessa.
Inspired by top open-source file manipulation tools (fzf, ripgrep, fd, Aider, Open-Interpreter):
- Sub-second filename search via /usr/bin/fd with intelligent exclusions
- Blazing-fast file content search via /usr/bin/rg (ripgrep)
- Deep reading and writing with line range support (.txt, .py, .md, .json, .csv, .docx)
- Surgical search-and-replace in files
- File management: copy, move/rename, safe deletion
- Directory organization: automatically sorts files by type (audio, docs, images, videos, code)
- Cloud storage integration (Google Drive, Nextcloud, Dropbox, OneDrive, GVFS)
"""
import os
import time
import shutil
import subprocess
from typing import List, Dict, Any, Optional
from docx import Document


class FileManager:
    def __init__(self, base_dirs: Optional[List[str]] = None):
        self.home = os.path.expanduser("~")
        if base_dirs is None:
            self.search_roots = [
                os.path.join(self.home, "Documentos"),
                os.path.join(self.home, "Documents"),
                os.path.join(self.home, "Descargas"),
                os.path.join(self.home, "Downloads"),
                os.path.join(self.home, "Escritorio"),
                os.path.join(self.home, "Desktop"),
                os.path.join(self.home, "Proyectos"),
                os.path.join(self.home, "Pictures"),
                os.path.join(self.home, "Imágenes"),
                self.home
            ]
            self.search_roots = [d for d in self.search_roots if os.path.isdir(d)]
        else:
            self.search_roots = base_dirs

        self.fd_bin = shutil.which("fd") or shutil.which("fdfind") or "/usr/bin/fd"
        self.rg_bin = shutil.which("rg") or "/usr/bin/rg"

    def get_cloud_directories(self) -> List[Dict[str, str]]:
        potential_cloud_paths = [
            ("Google Drive", os.path.join(self.home, "Google Drive")),
            ("Google Drive", os.path.join(self.home, "GoogleDrive")),
            ("Nextcloud", os.path.join(self.home, "Nextcloud")),
            ("Dropbox", os.path.join(self.home, "Dropbox")),
            ("OneDrive", os.path.join(self.home, "OneDrive")),
            ("kDrive", os.path.join(self.home, "kDrive")),
            ("KDE/GNOME GVFS Cloud", f"/run/user/{os.getuid()}/gvfs")
        ]

        active_clouds = []
        for name, path in potential_cloud_paths:
            if os.path.exists(path) and os.path.isdir(path):
                active_clouds.append({"name": name, "path": path})

        try:
            res = subprocess.run(["mount"], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    lower_line = line.lower()
                    if any(term in lower_line for term in ["google", "rclone", "nextcloud", "webdav", "fuse.gdrive"]):
                        parts = line.split(" on ")
                        if len(parts) > 1:
                            mount_point = parts[1].split(" type ")[0].strip()
                            if os.path.exists(mount_point):
                                active_clouds.append({"name": "Cloud Mount", "path": mount_point})
        except Exception:
            pass

        return active_clouds

    # === FILENAME SEARCH (fd) ===
    def search_files(
        self,
        query: str,
        location: str = "all",
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        clean_q = query.strip()
        if not clean_q:
            return []

        results = []
        seen = set()
        cloud_dirs = self.get_cloud_directories()
        cloud_paths = [c["path"] for c in cloud_dirs]

        target_roots = []
        if location in ("all", "cloud") and cloud_paths:
            target_roots.extend(cloud_paths)
        if location in ("all", "local"):
            target_roots.append(self.home)

        if self.fd_bin and os.path.exists(self.fd_bin):
            for root_dir in target_roots:
                if not os.path.exists(root_dir):
                    continue
                try:
                    cmd = [
                        self.fd_bin,
                        "-i", "-H",
                        "-E", ".git",
                        "-E", ".cache",
                        "-E", "node_modules",
                        "-E", ".venv",
                        "-E", "__pycache__",
                        "-E", ".cargo",
                        "--max-results", str(limit * 2),
                        clean_q,
                        root_dir
                    ]
                    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=6)
                    if proc.returncode == 0 and proc.stdout:
                        for line in proc.stdout.splitlines():
                            fpath = line.strip()
                            if fpath and fpath not in seen and os.path.exists(fpath):
                                seen.add(fpath)
                                is_cloud = any(fpath.startswith(cp) for cp in cloud_paths)
                                if location == "cloud" and not is_cloud:
                                    continue
                                stat = os.stat(fpath)
                                results.append({
                                    "filename": os.path.basename(fpath),
                                    "path": fpath,
                                    "size_bytes": stat.st_size,
                                    "size_str": self._format_size(stat.st_size),
                                    "extension": os.path.splitext(fpath)[1].lower(),
                                    "storage_type": "nube" if is_cloud else "local",
                                    "modified_str": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
                                })
                                if len(results) >= limit:
                                    return results
                except Exception as e:
                    print(f"[FileManager] Error en búsqueda fd: {e}")

        # Python os.walk fallback
        if len(results) < limit:
            search_list = cloud_paths if location == "cloud" else self.search_roots
            for root_dir in search_list:
                try:
                    for root, dirs, files in os.walk(root_dir):
                        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', '.venv')]
                        for file in files:
                            if file.startswith('.'):
                                continue
                            if clean_q.lower() in file.lower():
                                full_path = os.path.join(root, file)
                                if full_path not in seen and os.path.exists(full_path):
                                    seen.add(full_path)
                                    is_cloud = any(full_path.startswith(cp) for cp in cloud_paths)
                                    stat = os.stat(full_path)
                                    results.append({
                                        "filename": file,
                                        "path": full_path,
                                        "size_bytes": stat.st_size,
                                        "size_str": self._format_size(stat.st_size),
                                        "extension": os.path.splitext(file)[1].lower(),
                                        "storage_type": "nube" if is_cloud else "local",
                                        "modified_str": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
                                    })
                                    if len(results) >= limit:
                                        return results
                except PermissionError:
                    continue

        return results

    # === CONTENT SEARCH (ripgrep / rg) ===
    def search_file_content(
        self,
        query: str,
        directory: Optional[str] = None,
        file_pattern: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Searches text patterns inside files using ripgrep (/usr/bin/rg).
        Returns file path, line number, and matching line content.
        """
        clean_q = query.strip()
        if not clean_q:
            return []

        target_dir = directory if directory and os.path.isdir(directory) else self.home
        results = []

        if self.rg_bin and os.path.exists(self.rg_bin):
            cmd = [
                self.rg_bin,
                "-i", "--line-number", "--no-heading",
                "--max-count", "3",
                "-g", "!.git",
                "-g", "!node_modules",
                "-g", "!.venv",
                "-g", "!__pycache__",
                "--max-filesize", "10M"
            ]
            if file_pattern:
                cmd.extend(["-g", file_pattern])

            cmd.extend([clean_q, target_dir])

            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=8)
                if proc.returncode in (0, 1) and proc.stdout:
                    for line in proc.stdout.splitlines():
                        parts = line.split(":", 2)
                        if len(parts) >= 3:
                            fpath, line_no, content = parts[0], parts[1], parts[2]
                            results.append({
                                "file": fpath,
                                "filename": os.path.basename(fpath),
                                "line_number": int(line_no) if line_no.isdigit() else 0,
                                "match": content.strip()[:200]
                            })
                            if len(results) >= limit:
                                break
            except Exception as e:
                print(f"[FileManager] Error en ripgrep search: {e}")

        return results

    # === FILE READING & WRITING ===
    def read_file(
        self,
        filepath: str,
        start_line: int = 1,
        end_line: int = 150,
        max_bytes: int = 50000
    ) -> Dict[str, Any]:
        """Reads file content safely with line range support."""
        if not os.path.exists(filepath):
            return {"success": False, "error": f"Archivo no encontrado: {filepath}"}

        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext == ".docx":
                doc = Document(filepath)
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                text = "\n".join(paragraphs[start_line - 1:end_line])
                return {"success": True, "content": text, "total_paragraphs": len(paragraphs)}

            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                total = len(lines)
                selected = lines[max(0, start_line - 1):end_line]
                content = "".join(selected)[:max_bytes]
                return {
                    "success": True,
                    "content": content,
                    "start_line": start_line,
                    "end_line": min(end_line, total),
                    "total_lines": total
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, filepath: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
        """Creates or writes content to a file."""
        if os.path.exists(filepath) and not overwrite:
            return {"success": False, "error": f"El archivo '{filepath}' ya existe. Active overwrite si desea sobrescribirlo."}

        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "message": f"Archivo guardado exitosamente en '{filepath}'."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def replace_text_in_file(self, filepath: str, target_text: str, replacement_text: str) -> Dict[str, Any]:
        """Performs surgical find-and-replace in a text file."""
        if not os.path.exists(filepath):
            return {"success": False, "error": f"Archivo '{filepath}' no encontrado."}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if target_text not in content:
                return {"success": False, "error": "El texto objetivo no se encontró en el archivo."}

            new_content = content.replace(target_text, replacement_text, 1)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {"success": True, "message": f"Texto reemplazado en '{os.path.basename(filepath)}'."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # === FILE OPERATIONS (Copy, Move, Delete) ===
    def copy_file(self, src: str, dst: str) -> Dict[str, Any]:
        if not os.path.exists(src):
            return {"success": False, "error": f"Origen '{src}' no existe."}
        try:
            if os.path.isdir(dst):
                dst = os.path.join(dst, os.path.basename(src))
            shutil.copy2(src, dst)
            return {"success": True, "message": f"Copiado '{src}' a '{dst}'."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def move_file(self, src: str, dst: str) -> Dict[str, Any]:
        if not os.path.exists(src):
            return {"success": False, "error": f"Origen '{src}' no existe."}
        try:
            shutil.move(src, dst)
            return {"success": True, "message": f"Movido '{src}' a '{dst}'."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, filepath: str, safe_trash: bool = True) -> Dict[str, Any]:
        if not os.path.exists(filepath):
            return {"success": False, "error": f"Archivo '{filepath}' no existe."}
        try:
            if safe_trash and shutil.which("trash-put"):
                subprocess.run(["trash-put", filepath], check=True)
                return {"success": True, "message": f"'{os.path.basename(filepath)}' enviado a la papelera de reciclaje."}
            else:
                if os.path.isdir(filepath):
                    shutil.rmtree(filepath)
                else:
                    os.remove(filepath)
                return {"success": True, "message": f"'{os.path.basename(filepath)}' eliminado permanentemente."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # === DIRECTORY AUTO-ORGANIZATION ===
    def organize_directory(self, directory: str) -> Dict[str, Any]:
        """
        Organizes files in a directory into clean subfolders (Audio, Documentos, Imágenes, Videos, Código, Comprimidos).
        """
        if not os.path.isdir(directory):
            return {"success": False, "error": f"Directorio '{directory}' no existe."}

        categories = {
            "Audio_y_Voz": {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".opus", ".webm"},
            "Documentos": {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".odt", ".csv"},
            "Imagenes": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"},
            "Videos": {".mp4", ".mkv", ".avi", ".mov", ".webm"},
            "Codigo": {".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".rs", ".sh", ".json"},
            "Comprimidos": {".zip", ".tar", ".gz", ".xz", ".7z", ".rar"}
        }

        moved_count = 0
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path) and not item.startswith("."):
                    ext = os.path.splitext(item)[1].lower()
                    for cat, ext_set in categories.items():
                        if ext in ext_set:
                            dest_dir = os.path.join(directory, cat)
                            os.makedirs(dest_dir, exist_ok=True)
                            shutil.move(item_path, os.path.join(dest_dir, item))
                            moved_count += 1
                            break

            return {"success": True, "message": f"Se organizaron {moved_count} archivo(s) en '{directory}'."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # === DESKTOP INTEGRATION ===
    def open_file(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return f"El archivo '{filepath}' no existe."
        try:
            subprocess.Popen(["xdg-open", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abriendo '{os.path.basename(filepath)}'..."
        except Exception as e:
            return f"No se pudo abrir el archivo: {e}"

    def reveal_in_folder(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return f"El archivo '{filepath}' no existe."
        folder = os.path.dirname(filepath) if os.path.isfile(filepath) else filepath
        try:
            if shutil.which("dolphin"):
                subprocess.Popen(["dolphin", "--select", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["xdg-open", folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abriendo carpeta contenedora de '{os.path.basename(filepath)}'..."
        except Exception as e:
            return f"Error abriendo carpeta: {e}"

    def read_file_preview(self, filepath: str, max_chars: int = 2000) -> str:
        res = self.read_file(filepath, end_line=50, max_bytes=max_chars)
        if res.get("success"):
            return res.get("content", "")
        return res.get("error", "Error leyendo archivo")

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024.0:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024.0 * 1024.0):.1f} MB"
        else:
            return f"{size_bytes / (1024.0 * 1024.0 * 1024.0):.1f} GB"
