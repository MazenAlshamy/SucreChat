from datetime import timedelta
import secrets

from sqlalchemy.orm import Session

from app.errors import bad_request
from app.models.identity import CaptchaChallenge
from app.security import hash_token, new_id, tokens_match, utcnow

CAPTCHA_TTL_SECONDS = 600


def issue_captcha(db: Session) -> dict:
    left = secrets.randbelow(9) + 1
    right = secrets.randbelow(9) + 1
    answer = str(left + right)
    challenge = CaptchaChallenge(
        id=new_id(),
        answer_hash=hash_token(answer),
        expires_at=utcnow() + timedelta(seconds=CAPTCHA_TTL_SECONDS),
        consumed=False,
    )
    db.add(challenge)
    db.flush()
    return {
        "captcha_id": challenge.id,
        "question": f"ما ناتج {left} + {right}؟",
        "expires_in": CAPTCHA_TTL_SECONDS,
    }


def consume_captcha(db: Session, captcha_id: str, answer: str) -> None:
    cleaned_id = (captcha_id or "").strip()
    cleaned_answer = "".join((answer or "").split())
    if not cleaned_id or not cleaned_answer:
        raise bad_request("أجب عن سؤال التحقق")
    challenge = db.get(CaptchaChallenge, cleaned_id)
    if (
        challenge is None
        or challenge.consumed
        or challenge.expires_at <= utcnow()
        or not tokens_match(cleaned_answer, challenge.answer_hash)
    ):
        raise bad_request("إجابة التحقق غير صحيحة أو منتهية")
    challenge.consumed = True
    db.flush()
