from pydantic import BaseModel, Field


class CaptchaChallengeResponse(BaseModel):
    captcha_id: str
    question: str
    expires_in: int


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=40)
    last_name: str = Field(min_length=1, max_length=40)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=72)
    terms_accepted: bool
    captcha_id: str = Field(min_length=1, max_length=64)
    captcha_answer: str = Field(min_length=1, max_length=16)


class RegisterResponse(BaseModel):
    email: str
    verification_required: bool = True
    mail_sent: bool
    message: str


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=72)


class VerifyEmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=4, max_length=12)


class ResendVerificationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    captcha_id: str = Field(min_length=1, max_length=64)
    captcha_answer: str = Field(min_length=1, max_length=16)


class AccountUser(BaseModel):
    id: str
    display_name: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    email_verified: bool = False
    account_status: str = "guest"


class AccountSessionResponse(BaseModel):
    user: AccountUser
