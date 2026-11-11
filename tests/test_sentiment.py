from data_manager.services.sentiment import score_headline


def test_sentiment_positive():
    assert score_headline("Company reports record profit and strong growth") == "positive"


def test_sentiment_negative():
    assert score_headline("Shares fall after downgrade and weak outlook") == "negative"


def test_sentiment_neutral():
    assert score_headline("Company to hold annual general meeting") == "neutral"
