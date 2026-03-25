import secrets
import smtplib
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD


def generate_verification_code() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def send_verification_email(to_email: str, name: str, code: str) -> bool:
    if not SMTP_PASSWORD:
        print(f"[SMTP] 비밀번호 미설정. 인증 코드: {code} (개발 모드)")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "[멋쟁이사자처럼 순천대] 이메일 인증을 완료해주세요"
    msg["From"] = f"멋쟁이사자처럼 순천대 <{SMTP_USER}>"
    msg["To"] = to_email

    html = f"""
    <div style="font-family: 'Pretendard', sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #0d0d0d; color: #fff; border-radius: 16px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #FF7710; margin: 0; font-size: 24px;">LIKELION UNIV. x SCNU</h1>
            <p style="color: #888; margin-top: 8px;">PBL 과제 시스템 이메일 인증</p>
        </div>
        <div style="background: #1a1a1a; padding: 24px; border-radius: 12px; text-align: center;">
            <p style="color: #ccc; margin-bottom: 16px;">{name}님, 회원가입을 위해 아래 인증 코드를 입력해주세요.</p>
            <div style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #FF7710; padding: 16px; background: #0d0d0d; border-radius: 8px; display: inline-block;">
                {code}
            </div>
            <p style="color: #888; margin-top: 16px; font-size: 13px;">인증 코드는 회원가입 페이지에서 입력해주세요.<br>이메일 인증 후 운영진의 승인이 필요합니다.</p>
        </div>
        <p style="color: #555; font-size: 12px; text-align: center; margin-top: 16px;">본 메일은 발신 전용입니다.</p>
    </div>
    """

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[SMTP] 이메일 발송 실패: {e}")
        return False


def send_approval_notification(to_email: str, name: str, approved: bool) -> bool:
    if not SMTP_PASSWORD:
        print(f"[SMTP] 비밀번호 미설정. {'승인' if approved else '거절'} 알림 스킵")
        return True

    status = "승인" if approved else "거절"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[멋쟁이사자처럼 순천대] 회원가입이 {status}되었습니다"
    msg["From"] = f"멋쟁이사자처럼 순천대 <{SMTP_USER}>"
    msg["To"] = to_email

    if approved:
        body = f"""
        <div style="font-family: 'Pretendard', sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #0d0d0d; color: #fff; border-radius: 16px;">
            <h1 style="color: #FF7710; text-align: center;">회원가입 승인 완료!</h1>
            <p style="color: #ccc; text-align: center;">{name}님, 멋쟁이사자처럼 순천대 PBL 시스템에 오신 것을 환영합니다!</p>
            <div style="text-align: center; margin-top: 24px;">
                <a href="https://likelionscnu.site/pages/login.html" style="background: #FF7710; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">로그인하기</a>
            </div>
        </div>
        """
    else:
        body = f"""
        <div style="font-family: 'Pretendard', sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #0d0d0d; color: #fff; border-radius: 16px;">
            <h1 style="color: #ff4444; text-align: center;">회원가입 거절</h1>
            <p style="color: #ccc; text-align: center;">{name}님, 죄송합니다. 회원가입이 거절되었습니다. 문의사항은 운영진에게 연락해주세요.</p>
        </div>
        """

    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[SMTP] 이메일 발송 실패: {e}")
        return False
