import unittest

from services.probability_engine import calculate_market_probability


class ProbabilityEngineTests(unittest.TestCase):
    def test_no_market_data_gives_zero_confidence(self):
        result = calculate_market_probability({"macd_signal": "neutral"})
        self.assertEqual(result.confidence, 0)

    def test_full_market_data_keeps_confidence(self):
        result = calculate_market_probability({
            "price_usd": 110,
            "ema20": 100,
            "ema50": 90,
            "rsi": 62,
            "funding_rate": 0.0001,
            "macd_signal": "bullish",
            "market_structure": "bullish",
        })
        self.assertGreater(result.confidence, 0)


if __name__ == "__main__":
    unittest.main()
