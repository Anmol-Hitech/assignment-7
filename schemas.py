from pydantic import BaseModel,EmailStr
from typing import List,Optional
class CreateUser(BaseModel):
    username:str
    email:EmailStr
    password:str
    role:str
    grade:Optional[str] | None ="P"

class AdminLogin(BaseModel):
    name:str
    email:EmailStr
    password:str
    role:str
class StudentRes(BaseModel):
    name:str
    grade:str
class CustomRes(BaseModel):
    data:List[StudentRes]