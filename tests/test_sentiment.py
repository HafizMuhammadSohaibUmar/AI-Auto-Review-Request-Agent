from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from models.review_request import Sentiment
from services.sentiment import classify_sentiment


def _response(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("raw,expected", [
    ("POSITIVE", Sentiment.POSITIVE),
    ("NEUTRAL", Sentiment.NEUTRAL),
    ("NEGATIVE", Sentiment.NEGATIVE),
])
async def test_classify_sentiment_branches(raw, expected):
    with patch("services.sentiment.litellm.acompletion",
               new=AsyncMock(return_value=_response(raw))):
        assert await classify_sentiment("notes") == expected


@pytest.mark.asyncio
async def test_classify_sentiment_defaults_neutral_on_failure():
    with patch("services.sentiment.litellm.acompletion",
               new=AsyncMock(side_effect=RuntimeError("down"))):
        assert await classify_sentiment("notes") == Sentiment.NEUTRAL
