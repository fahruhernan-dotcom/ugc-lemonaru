"""Unit tests for GoogleFlowBrowserAgent (Hermes Hands & Feet on Google Flow)."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.flow_browser_agent import GoogleFlowBrowserAgent


def test_google_flow_browser_agent_init():
    mock_op = MagicMock()
    agent = GoogleFlowBrowserAgent(operator=mock_op)
    assert agent.operator == mock_op
    assert agent.driver is None


def test_google_flow_browser_agent_ensure_driver():
    mock_op = MagicMock()
    mock_driver = MagicMock()
    mock_op.start_driver.return_value = mock_driver

    agent = GoogleFlowBrowserAgent(operator=mock_op)
    driver = agent.ensure_driver()
    assert driver == mock_driver
    mock_op.start_driver.assert_called_once()


def test_google_flow_browser_agent_configure_settings():
    mock_op = MagicMock()
    mock_driver = MagicMock()
    mock_op.start_driver.return_value = mock_driver

    # Mock DOM elements
    mock_settings_btn = MagicMock()
    mock_never_radio = MagicMock()
    mock_chip = MagicMock()
    mock_save_btn = MagicMock()

    mock_driver.find_elements.side_effect = lambda by, selector: (
        [mock_settings_btn] if "setting" in selector else
        [mock_never_radio] if "Never" in selector else
        [mock_chip] if "9:16" in selector else
        [mock_save_btn] if "Save" in selector else []
    )

    agent = GoogleFlowBrowserAgent(operator=mock_op)
    res = agent.configure_agent_settings(confirm="Never", aspect_ratio="9:16")

    assert res["settings_opened"] is True
    assert res["confirm_set_to_never"] is True
    assert res["aspect_9_16_set"] is True
    assert res["saved"] is True
    mock_settings_btn.click.assert_called()
    mock_never_radio.click.assert_called()
    mock_chip.click.assert_called()
    mock_save_btn.click.assert_called()


def test_google_flow_browser_agent_create_character():
    mock_op = MagicMock()
    mock_driver = MagicMock()
    mock_op.start_driver.return_value = mock_driver

    mock_char_btn = MagicMock()
    mock_arch_chip = MagicMock()

    mock_driver.find_elements.side_effect = lambda by, selector: (
        [mock_char_btn] if "Character" in selector else
        [mock_arch_chip] if "The Professional" in selector else []
    )

    agent = GoogleFlowBrowserAgent(operator=mock_op)
    res = agent.create_fashion_character(
        name="Velora Model",
        base_archetype="The Professional"
    )

    assert res["character_name"] == "Velora Model"
    assert res["archetype"] == "The Professional"
    assert res["created"] is True
    mock_char_btn.click.assert_called()
    mock_arch_chip.click.assert_called()


def test_google_flow_browser_agent_submit_prompt():
    mock_op = MagicMock()
    mock_driver = MagicMock()
    mock_op.start_driver.return_value = mock_driver

    mock_input = MagicMock()
    mock_input.get_attribute.return_value = "Describe your character or scene..."
    mock_arrow_btn = MagicMock()

    mock_driver.find_elements.side_effect = lambda by, selector: (
        [mock_input] if "textarea" in selector else
        [mock_arrow_btn] if "generate" in selector else []
    )

    agent = GoogleFlowBrowserAgent(operator=mock_op)
    success = agent.submit_prompt("Chic Indonesian model in sage blazer 9:16", trigger_generate=True)

    assert success is True
    mock_input.click.assert_called()
    mock_input.clear.assert_called()
    mock_input.send_keys.assert_called_with("Chic Indonesian model in sage blazer 9:16")
    mock_arrow_btn.click.assert_called()
