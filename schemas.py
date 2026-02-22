from pydantic import BaseModel,EmailStr
from typing import List,Optional
class CreateUser(BaseModel):
    username:str
    email:EmailStr | None=None
    password:str
    role:str
    grade:Optional[str] | None ="P"
    teacher_id:Optional[int] | None=None

class AdminLogin(BaseModel):
    name:str
    email:str
    password:str
    role:str
class StudentRes(BaseModel):
    name:str
    grade:str

class CustomRes(BaseModel):
    data:List[StudentRes]

class ProfileRes(BaseModel):
    name:str
