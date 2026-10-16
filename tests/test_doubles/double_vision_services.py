class VisionServicesDouble:
    def __init__(self, offline_mode=True):
        self.offline_mode = offline_mode
        self.last_hash = None
        self.call_count = 0

    def build_grim_command(self, x, y, w, h, output_path="/dev/shm/crop.jpg"):
        geom = f"{int(x)},{int(y)} {int(w)}x{int(h)}"
        return ["grim", "-g", geom, "-t", "jpeg", "-q", "75", output_path]

    def compute_dhash_from_grid(self, grid_9x8):
        bits = 0
        for row in range(8):
            for col in range(8):
                bits <<= 1
                if grid_9x8[row][col] > grid_9x8[row][col + 1]:
                    bits |= 1
        return bits

    def hamming_distance(self, hash1, hash2):
        if hash1 is None or hash2 is None:
            return 64
        xor_val = hash1 ^ hash2
        return bin(xor_val).count("1")

    def should_skip_ai_analysis(self, current_hash, threshold=4):
        if self.last_hash is None:
            self.last_hash = current_hash
            return False
        dist = self.hamming_distance(self.last_hash, current_hash)
        if dist < threshold:
            return True
        self.last_hash = current_hash
        return False

    def generate_context_summary(self, activity="coding", tool="nvim", mood="deep_focus"):
        self.call_count += 1
        return {
            "activity": activity,
            "active_tool": tool,
            "user_mood": mood,
            "recommended_state": "perch" if mood == "deep_focus" else "wander"
        }
