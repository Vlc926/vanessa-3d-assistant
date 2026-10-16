import unittest
import asyncio
from unittest.mock import MagicMock, patch
from core.anime_tts import AnimeTTS, MASTER_VOICE_ID, ANIME_VOICE_PRESETS
from core.ai_intelligence_hub import AIIntelligenceHub
from core.brain import AssistantBrain

class TestOpenJarvisElevenLabsIntegration(unittest.TestCase):
    def setUp(self):
        self.tts = AnimeTTS()
        self.ai_hub = AIIntelligenceHub()
        self.mock_brain = AssistantBrain(
            memory=MagicMock(),
            sys_ctrl=MagicMock(),
            file_mgr=MagicMock(),
            music_det=MagicMock()
        )

    def test_elevenlabs_preset_configuration(self):
        self.assertEqual(MASTER_VOICE_ID, "n4GNpJP6Y2Nd09pDtetA")
        self.assertIn("gaby_elevenlabs", ANIME_VOICE_PRESETS)
        gaby = ANIME_VOICE_PRESETS["gaby_elevenlabs"]
        self.assertEqual(gaby["voice"], "n4GNpJP6Y2Nd09pDtetA")
        self.assertEqual(self.tts.voice, "n4GNpJP6Y2Nd09pDtetA")

    def test_elevenlabs_fallback_when_no_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(self.tts, "_get_elevenlabs_token", return_value=""):
                with patch.object(self.tts, "_generate_edge_tts", return_value="/tmp/test.mp3") as mock_edge:
                    with patch.object(self.tts, "_play_audio"):
                        asyncio.run(self.tts._speak_pipeline("Hola Amo Víctor", mood="happy"))
                        mock_edge.assert_called_once()

    def test_openjarvis_weather_capability(self):
        with patch("urllib.request.urlopen") as mock_url:
            mock_cm = MagicMock()
            mock_cm.__enter__.return_value.read.return_value = (
                '{"current_condition": [{"temp_C": "22", "FeelsLikeC": "22", "weatherDesc": [{"value": "Soleado"}], "humidity": "45", "windspeedKmph": "12"}],'
                '"nearest_area": [{"areaName": [{"value": "Monterrey"}], "country": [{"value": "Mexico"}]}]}'
            ).encode("utf-8")
            mock_url.return_value = mock_cm
            res = self.ai_hub.get_weather("Monterrey")
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["location"], "Monterrey")
            self.assertEqual(res["temp_c"], "22")
            self.assertIn("Amo Víctor", res["summary"])

    def test_openjarvis_morning_digest_structure(self):
        digest = self.ai_hub.get_morning_digest()
        self.assertIn("Buenos días, Amo Víctor", digest)
        self.assertIn("Estado de su equipo", digest)
        self.assertIn("CPU:", digest)
        self.assertIn("RAM libre:", digest)

    def test_brain_direct_command_weather(self):
        w_reply = asyncio.run(self.mock_brain.parse_and_execute_direct_command("Vanessa, ¿cómo está el clima?"))
        self.assertIsNotNone(w_reply)
        msg, mood, extra = w_reply
        self.assertEqual(mood, "happy")
        self.assertEqual(extra.get("action"), "weather")

    def test_brain_direct_command_morning_digest(self):
        d_reply = asyncio.run(self.mock_brain.parse_and_execute_direct_command("buenos días vanessa, dame el resumen de hoy"))
        self.assertIsNotNone(d_reply)
        msg, mood, extra = d_reply
        self.assertEqual(mood, "happy")
        self.assertEqual(extra.get("action"), "morning_digest")
        self.assertIn("Buenos días, Amo Víctor", msg)

    def test_brain_execute_action_weather_and_digest(self):
        act_weather = self.mock_brain._execute_action("weather location=Guadalajara")
        self.assertEqual(act_weather.get("action"), "weather")
        self.assertEqual(act_weather.get("location"), "Guadalajara")

        act_digest = self.mock_brain._execute_action("morning_digest")
        self.assertEqual(act_digest.get("action"), "morning_digest")
        self.assertIn("digest", act_digest)

if __name__ == "__main__":
    unittest.main()
