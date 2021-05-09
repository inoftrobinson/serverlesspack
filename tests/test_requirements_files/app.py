from pydantic import BaseModel
from typing import Optional


class RequestDataModel(BaseModel):
    loginToken: str

def login_with_google(data: dict):
    request_data = RequestDataModel(**data)
    from google.oauth2 import id_token
    from google.auth.transport.requests import Request as GoogleRequest
    user_infos: Optional[dict] = id_token.verify_oauth2_token(
        id_token=request_data.loginToken, request=GoogleRequest(), audience='token_id'
    )
    print(user_infos)
