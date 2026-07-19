import unittest
from services.trade_decision import generate_trade_decision, TradeDecision


class TradeDecisionTests(unittest.TestCase):
    def test_rule_1_buy(self):
        # price > EMA20 and price > EMA50 and RSI > 55 and Confluence Bullish > 70
        overview = {
            "symbol": "BTC",
            "price_usd": 64000.0,
            "ema20": 63000.0,
            "ema50": 62000.0,
            "rsi": 60.0,
            "confluence": {"bullish": 75},
            "high_24h_usd": 65000.0,
            "low_24h_usd": 61000.0
        }
        res = generate_trade_decision(overview)
        self.assertEqual(res.recommended_action, "BUY")
        self.assertEqual(res.market_bias, "Bullish")
        self.assertEqual(res.entry_type, "BUY")
        self.assertEqual(res.aggressive_entry, 63000.0)
        self.assertAlmostEqual(res.conservative_entry, 65000.0 * 1.001)
        self.assertAlmostEqual(res.stop_loss, 63000.0 * 0.99)
        self.assertEqual(res.take_profit_1, 65000.0)
        self.assertAlmostEqual(res.take_profit_2, 65000.0 * 1.025)
        # Risk = 63000 - 62370 = 630
        # Reward = 65000 - 63000 = 2000
        # RR = 2000 / 630 = 3.1746... -> 3.17
        self.assertAlmostEqual(res.risk_reward, 3.17)

    def test_rule_2_wait_between_emas(self):
        # price between EMA20 and EMA50 -> WAIT
        overview = {
            "symbol": "BTC",
            "price_usd": 62500.0,
            "ema20": 63000.0,
            "ema50": 62000.0,
            "rsi": 60.0,
            "confluence": {"bullish": 75}
        }
        res = generate_trade_decision(overview)
        self.assertEqual(res.recommended_action, "WAIT")
        self.assertEqual(res.market_bias, "Neutral")
        self.assertIsNone(res.aggressive_entry)

    def test_rule_2_wait_range_structure(self):
        # Market Structure == Range -> WAIT
        overview = {
            "symbol": "BTC",
            "price_usd": 64000.0,
            "ema20": 63000.0,
            "ema50": 62000.0,
            "rsi": 60.0,
            "confluence": {"bullish": 75},
            "market_structure": "Range"
        }
        res = generate_trade_decision(overview)
        self.assertEqual(res.recommended_action, "WAIT")
        self.assertEqual(res.market_bias, "Neutral")

    def test_rule_3_sell(self):
        # price < EMA20 and price < EMA50 and RSI < 45 and Confluence Bearish > 70
        overview = {
            "symbol": "BTC",
            "price_usd": 60000.0,
            "ema20": 61000.0,
            "ema50": 62000.0,
            "rsi": 40.0,
            "confluence": {"bearish": 80},
            "high_24h_usd": 63000.0,
            "low_24h_usd": 59000.0
        }
        res = generate_trade_decision(overview)
        self.assertEqual(res.recommended_action, "SELL")
        self.assertEqual(res.market_bias, "Bearish")
        self.assertEqual(res.entry_type, "SELL")
        self.assertAlmostEqual(res.aggressive_entry, 61000.0 * 0.999)
        self.assertAlmostEqual(res.conservative_entry, 59000.0 * 0.999)
        self.assertAlmostEqual(res.stop_loss, 61000.0 * 1.01)
        self.assertEqual(res.take_profit_1, 59000.0)

    def test_rule_4_crowded_longs(self):
        # Funding rate >= 0.0003 and price near 24h high resistance
        overview = {
            "symbol": "BTC",
            "price_usd": 64800.0,
            "ema20": 63000.0,
            "ema50": 62000.0,
            "rsi": 60.0,
            "confluence": {"bullish": 75},
            "high_24h_usd": 65000.0,
            "funding_rate": 0.0004
        }
        res = generate_trade_decision(overview)
        self.assertIn("Late longs becoming crowded.", res.reason)

    def test_rule_5_short_squeeze(self):
        # Funding rate < 0 and bullish trend
        overview = {
            "symbol": "BTC",
            "price_usd": 64000.0,
            "ema20": 63000.0,
            "ema50": 62000.0,
            "rsi": 60.0,
            "confluence": {"bullish": 75},
            "funding_rate": -0.0001
        }
        res = generate_trade_decision(overview)
        self.assertIn("Potential short squeeze.", res.reason)

    def test_rule_6_breakout(self):
        # Open Interest increases and breakout detected
        overview = {
            "symbol": "BTC",
            "price_usd": 64000.0,
            "ema20": 63000.0,
            "ema50": 62000.0,
            "rsi": 60.0,
            "confluence": {"bullish": 75},
            "oi_increases": True,
            "breakout_detected": True
        }
        res = generate_trade_decision(overview)
        self.assertIn("Breakout supported by derivatives participation.", res.reason)

    def test_trade_quality_5(self):
        # quality is 5 when bullish score > 85, confidence > 85, trend != Range, break of structure detected
        overview = {
            "symbol": "BTC",
            "price_usd": 64000.0,
            "ema20": 63000.0,
            "ema50": 62000.0,
            "rsi": 60.0,
            "confluence": {"bullish": 90},
            "trend": "Bullish",
            "break_of_structure": True
        }
        res = generate_trade_decision(overview)
        self.assertEqual(res.trade_quality, 5)

    def test_trade_quality_other(self):
        # Otherwise quality should be logical (e.g. 3 or 4)
        overview = {
            "symbol": "BTC",
            "price_usd": 64000.0,
            "ema20": 63000.0,
            "ema50": 62000.0,
            "rsi": 60.0,
            "confluence": {"bullish": 75},
            "trend": "Bullish"
        }
        res = generate_trade_decision(overview)
        self.assertTrue(1 <= res.trade_quality <= 4)

    def test_graceful_degradation(self):
        # missing fields check
        res = generate_trade_decision({})
        self.assertEqual(res.recommended_action, "WAIT")
        self.assertEqual(res.market_bias, "Neutral")
        self.assertIsNone(res.aggressive_entry)
        self.assertIsNone(res.stop_loss)
        self.assertIsNone(res.take_profit_1)
        self.assertIsNone(res.risk_reward)
        self.assertEqual(res.entry_type, "n/a")


if __name__ == "__main__":
    unittest.main()
