import html as html_lib
import secrets
import smtplib
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SITE_URL


def generate_verification_code() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def _send_html_email(to_email: str, subject: str, html_body: str) -> bool:
    """SMTP로 HTML 이메일을 전송하는 공통 헬퍼"""
    if not SMTP_PASSWORD:
        print(f"[SMTP] 비밀번호 미설정. 이메일 발송 건너뜀: {subject}")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"멋쟁이사자처럼 순천대 <{SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[SMTP] 이메일 발송 실패: {type(e).__name__}")
        return False


def send_verification_email(to_email: str, name: str, code: str) -> bool:
    safe_name = html_lib.escape(name)

    html = f"""
    <div style="font-family: 'Pretendard', sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #0d0d0d; color: #fff; border-radius: 16px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #FF7710; margin: 0; font-size: 24px;">LIKELION UNIV. x SCNU</h1>
            <p style="color: #888; margin-top: 8px;">PBL 과제 시스템 이메일 인증</p>
        </div>
        <div style="background: #1a1a1a; padding: 24px; border-radius: 12px; text-align: center;">
            <p style="color: #ccc; margin-bottom: 16px;">{safe_name}님, 회원가입을 위해 아래 인증 코드를 입력해주세요.</p>
            <div style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #FF7710; padding: 16px; background: #0d0d0d; border-radius: 8px; display: inline-block;">
                {code}
            </div>
            <p style="color: #888; margin-top: 16px; font-size: 13px;">인증 코드는 회원가입 페이지에서 입력해주세요.<br>이메일 인증 후 운영진의 승인이 필요합니다.</p>
        </div>
        <p style="color: #555; font-size: 12px; text-align: center; margin-top: 16px;">본 메일은 발신 전용입니다.</p>
    </div>
    """

    return _send_html_email(to_email, "[멋쟁이사자처럼 순천대] 이메일 인증을 완료해주세요", html)


def send_approval_notification(to_email: str, name: str, approved: bool) -> bool:
    safe_name = html_lib.escape(name)
    status = "승인" if approved else "거절"

    if approved:
        body = f"""
        <div style="font-family: 'Pretendard', sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #0d0d0d; color: #fff; border-radius: 16px;">
            <h1 style="color: #FF7710; text-align: center;">회원가입 승인 완료!</h1>
            <p style="color: #ccc; text-align: center;">{safe_name}님, 멋쟁이사자처럼 순천대 PBL 시스템에 오신 것을 환영합니다!</p>
            <div style="text-align: center; margin-top: 24px;">
                <a href="{SITE_URL}/pages/login.html" style="background: #FF7710; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">로그인하기</a>
            </div>
        </div>
        """
    else:
        body = f"""
        <div style="font-family: 'Pretendard', sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #0d0d0d; color: #fff; border-radius: 16px;">
            <h1 style="color: #ff4444; text-align: center;">회원가입 거절</h1>
            <p style="color: #ccc; text-align: center;">{safe_name}님, 죄송합니다. 회원가입이 거절되었습니다. 문의사항은 운영진에게 연락해주세요.</p>
        </div>
        """

    return _send_html_email(to_email, f"[멋쟁이사자처럼 순천대] 회원가입이 {status}되었습니다", body)


def send_review_notification(
    to_email: str, name: str, mission_number: int, mission_title: str,
    passed: bool, comment: str | None = None,
) -> bool:
    safe_name = html_lib.escape(name)
    safe_title = html_lib.escape(mission_title)
    safe_comment = html_lib.escape(comment) if comment else ""
    status = "합격" if passed else "반려"
    color = "#4ade80" if passed else "#f87171"
    icon = "🎉" if passed else "📝"

    comment_section = ""
    if safe_comment:
        comment_section = f"""
            <div style="background: #0d0d0d; padding: 16px; border-radius: 8px; margin-top: 16px; border-left: 3px solid {color};">
                <p style="color: #888; font-size: 13px; margin: 0 0 8px;">운영진 코멘트</p>
                <p style="color: #ccc; margin: 0;">{safe_comment}</p>
            </div>
        """

    action_text = "다음 미션도 화이팅!" if passed else "피드백을 확인하고 다시 제출해보세요!"

    html = f"""
    <div style="font-family: 'Pretendard', sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #0d0d0d; color: #fff; border-radius: 16px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #FF7710; margin: 0; font-size: 24px;">LIKELION UNIV. x SCNU</h1>
            <p style="color: #888; margin-top: 8px;">PBL 과제 검사 결과</p>
        </div>
        <div style="background: #1a1a1a; padding: 24px; border-radius: 12px; text-align: center;">
            <p style="font-size: 32px; margin: 0;">{icon}</p>
            <h2 style="color: {color}; margin: 12px 0 8px;">Mission {str(mission_number).zfill(2)} {status}</h2>
            <p style="color: #fff; font-weight: 600; margin: 0;">{safe_title}</p>
            <p style="color: #ccc; margin-top: 16px;">{safe_name}님, 제출하신 과제가 <strong style="color: {color};">{status}</strong> 처리되었습니다.</p>
            {comment_section}
            <p style="color: #888; margin-top: 16px; font-size: 14px;">{action_text}</p>
        </div>
        <div style="text-align: center; margin-top: 24px;">
            <a href="{SITE_URL}/pages/my" style="background: #FF7710; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">내 현황 확인하기</a>
        </div>
        <p style="color: #555; font-size: 12px; text-align: center; margin-top: 16px;">본 메일은 발신 전용입니다.</p>
    </div>
    """

    return _send_html_email(to_email, f"[멋쟁이사자처럼 순천대] Mission {str(mission_number).zfill(2)} {status} 알림", html)
