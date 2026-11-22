from unittest.mock import patch

import pytest

import config
from utils.chat_filter import is_owner


@pytest.fixture(autouse=True)
def owner(monkeypatch):
    monkeypatch.setattr(config, "OWNER_CHAT_ID", "111")


def test_is_owner():
    assert is_owner("111")
    assert is_owner(111)
    assert not is_owner("222")


def test_no_owner_configured_means_nobody(monkeypatch):
    monkeypatch.setattr(config, "OWNER_CHAT_ID", None)
    assert not is_owner("111")
    monkeypatch.setattr(config, "OWNER_CHAT_ID", "")
    assert not is_owner("111")


def test_stranger_cannot_see_portfolio():
    from core import command_router

    with patch.object(command_router, "send_message") as send, \
         patch("services.portfolio_service.handle_portfolio_command") as handler:
        command_router.route_command("222", "/portfolio")
    handler.assert_not_called()
    assert "private" in send.call_args[0][1]


def test_owner_can_see_portfolio():
    from core import command_router

    with patch("services.portfolio_service.handle_portfolio_command") as handler:
        command_router.route_command("111", "/portfolio")
    handler.assert_called_once_with("111")


def test_stranger_gets_no_position_section():
    from core import command_router

    with patch("services.portfolio_service.get_position") as get_position:
        command_router.send_position_section("222", "/analyze BTC")
    get_position.assert_not_called()


def test_analysis_card_skips_position_when_asked():
    import services.report_card as rc

    with patch("services.okx_service.get_market_overview", return_value={}), \
         patch("services.opportunity_scanner.calculate_opportunity_score", return_value=None), \
         patch("services.local_narrator.build_tactical_report", return_value={}), \
         patch.object(rc, "get_take", return_value=""), \
         patch.object(rc, "render_card", return_value="card") as render, \
         patch("services.portfolio_service.get_position") as get_position:
        rc.build_analysis_card("BTC", include_position=False)
    get_position.assert_not_called()
    assert render.call_args[0][2] is None
