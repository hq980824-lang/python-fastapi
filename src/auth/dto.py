from pydantic import BaseModel, EmailStr

class SendCodeDto(BaseModel):
    email: EmailStr

class EmailLoginDto(BaseModel):
    email: EmailStr
    code: str