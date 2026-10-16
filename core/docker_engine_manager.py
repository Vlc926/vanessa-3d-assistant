import os
import shutil
import subprocess

class DockerEngineManager:
    def __init__(self, root_dir=None):
        if root_dir is None:
            self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        else:
            self.root_dir = os.path.abspath(root_dir)
        self.compose_file = os.path.join(self.root_dir, "deploy", "docker", "docker-compose.yml")
        self.local_server_script = os.path.join(self.root_dir, "deploy", "docker", "engine_server.py")
        self.local_proc = None
        self.port = 8899

    def _run_docker(self, args, timeout=15):
        if not shutil.which("docker"):
            return None
        try:
            res = subprocess.run(
                ["docker"] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True
            )
            if res.returncode == 0:
                return res
        except Exception:
            pass
        if shutil.which("newgrp"):
            try:
                cmd = "docker " + " ".join(args) + "\n"
                res = subprocess.run(
                    ["newgrp", "docker"],
                    input=cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    text=True
                )
                if res.returncode == 0:
                    return res
            except Exception:
                pass
        return None

    def is_docker_available(self):
        res = self._run_docker(["info"], timeout=3)
        return res is not None

    def start_engine(self, force_docker=False):
        if self.is_docker_available():
            res = self._run_docker(["compose", "-f", self.compose_file, "up", "-d"], timeout=30)
            if res is not None:
                return {
                    "mode": "docker",
                    "status": "running",
                    "url": f"http://127.0.0.1:{self.port}"
                }

        if force_docker:
            return {
                "mode": "docker",
                "status": "failed",
                "error": "Docker is not available or failed to start."
            }

        return self.start_native_fallback()

    def start_native_fallback(self):
        if self.is_port_in_use(self.port):
            return {
                "mode": "native",
                "status": "already_running",
                "url": f"http://127.0.0.1:{self.port}"
            }
        try:
            self.local_proc = subprocess.Popen(
                ["python3", "-u", self.local_server_script, str(self.port), self.root_dir],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return {
                "mode": "native",
                "status": "running",
                "pid": self.local_proc.pid,
                "url": f"http://127.0.0.1:{self.port}"
            }
        except Exception as e:
            return {
                "mode": "native",
                "status": "error",
                "error": str(e)
            }

    def stop_engine(self):
        if self.is_docker_available():
            self._run_docker(["compose", "-f", self.compose_file, "down"], timeout=10)
        if self.local_proc:
            try:
                self.local_proc.terminate()
                self.local_proc.wait(timeout=2)
            except Exception:
                try:
                    self.local_proc.kill()
                except Exception:
                    pass
            self.local_proc = None

    def is_port_in_use(self, port):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def get_status(self):
        docker_available = self.is_docker_available()
        port_active = self.is_port_in_use(self.port)
        active_mode = "none"
        if port_active:
            active_mode = "docker" if docker_available else "native"
        return {
            "docker_installed": shutil.which("docker") is not None,
            "docker_daemon_active": docker_available,
            "port_active": port_active,
            "active_mode": active_mode,
            "engine_url": f"http://127.0.0.1:{self.port}"
        }
