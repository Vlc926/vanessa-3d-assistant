import unittest
from core.sensory_broker import (
    SensoryBroker,
    SensoryEventType,
    EmotionalTier,
    ScreenContextEvent,
    TextStimulusEvent,
    MediaStreamEvent,
    CursorProximityEvent
)

class MockVrmWidget:
    def __init__(self):
        self.dispatched_payloads = []

    def dispatch_sensory_event(self, payload: dict):
        self.dispatched_payloads.append(payload)

class TestSensoryBroker(unittest.TestCase):
    def setUp(self):
        self.broker = SensoryBroker()
        self.mock_widget = MockVrmWidget()
        self.broker.set_vrm_widget(self.mock_widget)

    def test_salience_calculation(self):
        sal_zero = self.broker.calculate_salience(0.0, 0.0, 0.0)
        self.assertAlmostEqual(sal_zero, 0.0, places=4)

        sal_max = self.broker.calculate_salience(1.0, 1.0, 1.0)
        self.assertAlmostEqual(sal_max, 1.0, places=4)

        sal_neg = self.broker.calculate_salience(-0.8, 0.5, 0.4)
        expected = (0.35 * 0.8) + (0.40 * 0.5) + (0.25 * 0.4)
        self.assertAlmostEqual(sal_neg, expected, places=4)

    def test_emotional_tier_thresholds(self):
        self.assertEqual(self.broker.evaluate_tier(0.15), EmotionalTier.TIER_1_BASELINE)
        self.assertEqual(self.broker.evaluate_tier(0.39), EmotionalTier.TIER_1_BASELINE)
        self.assertEqual(self.broker.evaluate_tier(0.40), EmotionalTier.TIER_2_EXAGGERATED)
        self.assertEqual(self.broker.evaluate_tier(0.77), EmotionalTier.TIER_2_EXAGGERATED)
        self.assertEqual(self.broker.evaluate_tier(0.78), EmotionalTier.TIER_3_CHIBI_MORPH)
        self.assertEqual(self.broker.evaluate_tier(1.00), EmotionalTier.TIER_3_CHIBI_MORPH)

    def test_dispatch_screen_context(self):
        received = []
        self.broker.subscribe(lambda p: received.append(p))

        self.broker.dispatch_screen_context(
            window_id="0x123",
            app_class="kitty",
            title="zsh - terminal",
            bbox=(100, 100, 800, 600),
            focus_state=True
        )

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["type"], SensoryEventType.SCREEN_CONTEXT.value)
        self.assertEqual(received[0]["data"]["app_class"], "kitty")
        self.assertEqual(received[0]["salience"], 0.45)
        self.assertEqual(received[0]["tier"], int(EmotionalTier.TIER_2_EXAGGERATED))

        self.assertEqual(len(self.mock_widget.dispatched_payloads), 1)

    def test_dispatch_text_stimulus(self):
        received = []
        self.broker.subscribe(lambda p: received.append(p))

        self.broker.dispatch_text_stimulus(
            category="dialogue",
            valence=-0.9,
            arousal=0.9,
            intensity=0.85,
            raw_text="¡Amo Víctor, no haga eso!"
        )

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["type"], SensoryEventType.TEXT_STIMULUS.value)
        self.assertGreaterEqual(received[0]["salience"], 0.78)
        self.assertEqual(received[0]["tier"], int(EmotionalTier.TIER_3_CHIBI_MORPH))

    def test_dispatch_media_stream(self):
        received = []
        self.broker.subscribe(lambda p: received.append(p))

        self.broker.dispatch_media_stream(
            media_type="music",
            title="Bury the Light",
            artist="Casey Edwards",
            loudness=0.85,
            bpm=160.0,
            duration=300.0
        )

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["type"], SensoryEventType.MEDIA_STREAM.value)
        self.assertGreaterEqual(received[0]["salience"], 0.40)

    def test_dispatch_cursor_proximity(self):
        received = []
        self.broker.subscribe(lambda p: received.append(p))

        self.broker.dispatch_cursor_proximity(
            cx=400.0,
            cy=300.0,
            vx=10.0,
            vy=5.0,
            dist=120.0
        )

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["type"], SensoryEventType.CURSOR_PROXIMITY.value)
        self.assertGreater(received[0]["salience"], 0.70)

    def test_unsubscribe(self):
        received = []
        sub = lambda p: received.append(p)
        self.broker.subscribe(sub)
        self.broker.dispatch_cursor_proximity(0, 0, 0, 0, 100)
        self.assertEqual(len(received), 1)

        self.broker.unsubscribe(sub)
        self.broker.dispatch_cursor_proximity(0, 0, 0, 0, 100)
        self.assertEqual(len(received), 1)

if __name__ == "__main__":
    unittest.main()
