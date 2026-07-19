import unittest
from services.volume_analysis import analyze_volume


class VolumeAnalysisTests(unittest.TestCase):
    def test_empty_history(self):
        # Checks graceful handling of empty history
        res = analyze_volume(100.0, [])
        self.assertEqual(res["average_volume"], 0.0)
        self.assertEqual(res["volume_ratio"], 0.0)
        self.assertEqual(res["strength"], "Normal")
        self.assertEqual(res["confirmation"], "Neutral")

    def test_none_history(self):
        # Checks handling of None list
        res = analyze_volume(100.0, None)
        self.assertEqual(res["average_volume"], 0.0)
        self.assertEqual(res["confirmation"], "Neutral")

    def test_zero_current_volume(self):
        # Checks when current volume is zero
        history = [100.0] * 20
        res = analyze_volume(0.0, history)
        self.assertEqual(res["current_volume"], 0.0)
        self.assertEqual(res["volume_ratio"], 0.0)
        self.assertEqual(res["strength"], "Very Low")

    def test_zero_average_volume(self):
        # Checks division by zero protection when average is zero
        history = [0.0] * 20
        res = analyze_volume(100.0, history)
        self.assertEqual(res["average_volume"], 0.0)
        self.assertEqual(res["volume_ratio"], 0.0)
        self.assertEqual(res["volume_change_percent"], 0.0)

    def test_below_average_very_low(self):
        # Ratio < 0.60: current = 50, avg = 100
        history = [100.0] * 20
        res = analyze_volume(50.0, history, price_change_percent=2.5)
        self.assertEqual(res["strength"], "Very Low")
        self.assertEqual(res["confirmation"], "Weak Breakout")
        self.assertIn("below average", res["summary"])

    def test_below_average_low(self):
        # Ratio 0.60 - 0.85: current = 70, avg = 100
        history = [100.0] * 20
        res = analyze_volume(70.0, history, price_change_percent=2.5)
        self.assertEqual(res["strength"], "Low")
        self.assertEqual(res["confirmation"], "Weak Breakout")
        self.assertIn("below average", res["summary"])

    def test_normal_volume_bullish(self):
        # Ratio 0.85 - 1.15: current = 100, avg = 100
        history = [100.0] * 20
        res = analyze_volume(100.0, history, price_change_percent=2.5)
        self.assertEqual(res["strength"], "Normal")
        self.assertEqual(res["confirmation"], "Bullish Confirmation")

    def test_above_average_high(self):
        # Ratio 1.15 - 1.50: current = 130, avg = 100
        history = [100.0] * 20
        res = analyze_volume(130.0, history, price_change_percent=2.5)
        self.assertEqual(res["strength"], "High")
        self.assertEqual(res["confirmation"], "Strong Bullish Confirmation")
        self.assertIn("above the 20-period average", res["summary"])

    def test_extreme_volume_very_high(self):
        # Ratio > 1.50: current = 200, avg = 100
        history = [100.0] * 20
        res = analyze_volume(200.0, history, price_change_percent=2.5)
        self.assertEqual(res["strength"], "Very High")
        self.assertEqual(res["confirmation"], "Strong Bullish Confirmation")

    def test_capitulation(self):
        # Price falling and volume Very High: current = 200, avg = 100, change < 0
        history = [100.0] * 20
        res = analyze_volume(200.0, history, price_change_percent=-3.0)
        self.assertEqual(res["strength"], "Very High")
        self.assertEqual(res["confirmation"], "Capitulation")

    def test_distribution_warning(self):
        # Price falling and volume High: current = 130, avg = 100, change < 0
        history = [100.0] * 20
        res = analyze_volume(130.0, history, price_change_percent=-1.5)
        self.assertEqual(res["strength"], "High")
        self.assertEqual(res["confirmation"], "Distribution Warning")

    def test_neutral_flat_price(self):
        # Flat price (0.0 change) and High volume should result in Neutral
        history = [100.0] * 20
        res = analyze_volume(130.0, history, price_change_percent=0.0)
        self.assertEqual(res["confirmation"], "Neutral")

    def test_invalid_volume_input_string(self):
        # Test handling of strings instead of floats
        history = ["100.0", "invalid", "100.0"]
        res = analyze_volume("120.0", history, price_change_percent="1.5")
        self.assertEqual(res["current_volume"], 120.0)
        self.assertEqual(res["average_volume"], 100.0)
        self.assertEqual(res["strength"], "High")
        self.assertEqual(res["confirmation"], "Strong Bullish Confirmation")

    def test_history_less_than_20(self):
        # History length less than 20: list of 5 elements
        history = [100.0, 110.0, 90.0, 100.0, 100.0]
        res = analyze_volume(100.0, history)
        self.assertEqual(res["average_volume"], 100.0)

    def test_history_more_than_20(self):
        # History length > 20: only last 20 elements are used
        history = [9999.0] * 10 + [100.0] * 20
        res = analyze_volume(100.0, history)
        # If the first 10 items were used, average would be much higher
        self.assertEqual(res["average_volume"], 100.0)

    def test_summary_content_positive(self):
        history = [100.0] * 20
        res = analyze_volume(134.0, history, price_change_percent=1.0)
        self.assertEqual(res["confirmation"], "Strong Bullish Confirmation")
        self.assertIn("34% above the 20-period average", res["summary"])
        self.assertIn("Buyers are participating", res["summary"])


if __name__ == "__main__":
    unittest.main()
