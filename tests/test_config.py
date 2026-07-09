from config import Settings


def test_google_review_url_uses_demo_url_for_placeholder_place_id():
    settings = Settings(
        gbp_place_id="your_google_business_profile_place_id",
        demo_review_url="https://example.com/demo-reviews",
    )

    assert settings.google_review_url == "https://example.com/demo-reviews"


def test_google_review_url_uses_place_id_when_configured():
    settings = Settings(gbp_place_id="ChIJ123")

    assert settings.google_review_url == "https://search.google.com/local/writereview?placeid=ChIJ123"
