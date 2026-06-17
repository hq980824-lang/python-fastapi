from http import HTTPStatus
from fastapi import HTTPException
from src.auth.dto import EmailLoginDto, SendCodeDto
from src.common.route import create_router
from src.utils.email_util import EmailUtil
from src.utils.jwt_util import JwtUtil

verify_code_store = {}

router = create_router(prefix="/auth", tags=["登录鉴权"])

@router.post("/send-code")
def send_email_code(dto: SendCodeDto):
    code = EmailUtil.generate_code()
    verify_code_store[dto.email] = code
    print(f"邮箱：{dto.email}，本次登录验证码：{code}")
    return code

@router.post("/login")
def email_login(dto: EmailLoginDto):
    if dto.email not in verify_code_store:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="清先获取邮箱验证码")
    real_code = verify_code_store[dto.email]
    if real_code != dto.code:
       raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="验证码错误")

    token = JwtUtil.create_access_token(subject=dto.email)
    del verify_code_store[dto.email]
    return {
        "token": token
    }