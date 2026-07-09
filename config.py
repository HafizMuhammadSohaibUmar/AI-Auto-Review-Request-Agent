"""Application configuration for the review request agent."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    business_id: str = "default-business"
    business_name: str = "Acme Home Services"

    host: str = "0.0.0.0"
    port: int = 8004
    public_base_url: str = "http://localhost:8004"
    log_level: str = "INFO"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    owner_phone_number: str = ""
    validate_twilio_signature: bool = True
    sms_dry_run: bool = False

    mistral_api_key: str = ""
    sentiment_model: str = "mistral/ministral-3b-latest"
    llm_timeout_seconds: float = 3.0

    supabase_url: str = ""
    supabase_key: str = ""

    gbp_place_id: str = ""
    gbp_account_id: str = ""
    gbp_location_id: str = ""
    gbp_access_token: str = ""
    gbp_review_match_window_days: int = 14

    jobber_webhook_secret: str = ""
    jobber_signature_header: str = "X-Jobber-Signature"
    housecallpro_webhook_secret: str = ""
    housecallpro_signature_header: str = "X-HousecallPro-Signature"
    internal_webhook_secret: str = ""
    manual_trigger_api_key: str = ""
    demo_mode_enabled: bool = True
    demo_owner_phone_number: str = "+15550002222"

    dedup_window_days: int = 90
    followup_delay_hours: int = 48

    @property
    def google_review_url(self) -> str:
        return f"https://search.google.com/local/writereview?placeid={self.gbp_place_id}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
