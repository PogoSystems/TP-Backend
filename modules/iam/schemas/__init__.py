from pydantic import BaseModel


class CompleteProfileRequest(BaseModel):
    """
    DTO with the information that the API asks to create a new user
    """
    name: str
    last_name: str
    college:str
    major:str

class UserResponse(BaseModel):
    """
    DTO with the user information that is returned from the API
    """
    name: str
    last_name: str
    college: str
    major: str

    model_config = {"from_attributes": True}