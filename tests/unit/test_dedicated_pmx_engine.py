import unittest
import os
from core.model_optimizer import ModelOptimizer, OFFICIAL_ZZZ_MODELS
from core.docker_engine_manager import DockerEngineManager

class TestDedicatedPMXEngine(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.optimizer = ModelOptimizer()

    def test_official_models_catalog_keys(self):
        catalog = self.optimizer.get_official_catalog()
        expected = ["burnice_white", "ellen_joe", "jane_doe", "anby_demara", "nicole_demara", "hoshimi_miyabi"]
        for key in expected:
            self.assertIn(key, catalog)
            meta = catalog[key]
            self.assertTrue(os.path.exists(meta["pmx_path"]), f"PMX file {meta['pmx_path']} must exist")
            self.assertGreater(meta["scale"], 0.05)
            self.assertLess(meta["scale"], 0.15)
            self.assertGreater(meta["camera_distance"], 2.0)
            self.assertIn("arm_rest", meta)
            self.assertIn("left", meta["arm_rest"])
            self.assertIn("right", meta["arm_rest"])

    def test_model_profiles_json_generation(self):
        results = self.optimizer.optimize_all_models()
        self.assertEqual(len(results), 6)
        for model_id, prof in results.items():
            self.assertEqual(prof["model_id"], model_id)
            prof_file = os.path.join(self.root_dir, "models", "pmx_models", model_id, "model_profile.json")
            self.assertTrue(os.path.exists(prof_file))
            self.assertGreater(prof["file_size"], 2000000)

    def test_docker_engine_manager_status_structure(self):
        mgr = DockerEngineManager(self.root_dir)
        st = mgr.get_status()
        self.assertIn("docker_installed", st)
        self.assertIn("docker_daemon_active", st)
        self.assertIn("port_active", st)
        self.assertIn("active_mode", st)
        self.assertIn("engine_url", st)
        self.assertEqual(st["engine_url"], "http://127.0.0.1:8899")

    def test_docker_engine_compose_and_dockerfile_exist(self):
        compose_path = os.path.join(self.root_dir, "deploy", "docker", "docker-compose.yml")
        dockerfile_path = os.path.join(self.root_dir, "deploy", "docker", "Dockerfile.engine")
        script_path = os.path.join(self.root_dir, "scripts", "docker_graphics_engine.sh")
        self.assertTrue(os.path.exists(compose_path))
        self.assertTrue(os.path.exists(dockerfile_path))
        self.assertTrue(os.path.exists(script_path))

    def test_docker_compose_resource_limits(self):
        compose_path = os.path.join(self.root_dir, "deploy", "docker", "docker-compose.yml")
        with open(compose_path, "r", encoding="utf-8") as fp:
            content = fp.read()
        self.assertIn("cpus: '1.0'", content)
        self.assertIn("memory: 512M", content)

    def test_js_dedicated_controller_exists(self):
        js_path = os.path.join(self.root_dir, "ui", "vrm", "dedicated_pmx_controller.js")
        self.assertTrue(os.path.exists(js_path))
        with open(js_path, "r", encoding="utf-8") as fp:
            content = fp.read()
        self.assertIn("DedicatedPMXController", content)
        self.assertIn("burnice_white", content)
        self.assertIn("ellen_joe", content)
        self.assertIn("jane_doe", content)
        self.assertIn("anby_demara", content)
        self.assertIn("nicole_demara", content)
        self.assertIn("hoshimi_miyabi", content)

if __name__ == "__main__":
    unittest.main()
