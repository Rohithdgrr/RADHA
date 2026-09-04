from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class UserRead(BaseModel):
    id: str
    email: EmailStr
    display_name: str | None = None
    created_at: datetime
    last_login: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
