set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if command -v docker >/dev/null 2>&1; then
    docker compose up -d --build
    echo "ZZZ Isolated Simulation Container running on port 9876"
elif command -v podman >/dev/null 2>&1; then
    podman compose up -d --build
    echo "ZZZ Isolated Simulation Container running via podman on port 9876"
else
    echo "Docker or Podman not installed on host. Running isolated Python background simulation."
    python3 simulation_server.py &
    echo "Native isolated physics daemon started."
fi
