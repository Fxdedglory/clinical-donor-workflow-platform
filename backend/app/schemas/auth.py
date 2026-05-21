from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserSession(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    full_name: str
    display_name: str | None = None
    email: str
    role_name: str
    permissions: list[str]
    last_login: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserSession


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginAudit(BaseModel):
    username: str
    ip_address: str | None = None
