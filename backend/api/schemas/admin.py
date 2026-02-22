from pydantic import BaseModel
from typing import List

class UserRoleUpdate(BaseModel):
    roles: List[str]
