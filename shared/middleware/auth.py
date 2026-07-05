from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient, PyJWKClientError

from core.settings import settings

bearer_scheme= HTTPBearer()

# url where the public keys can be retrieved from Supabase
_jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
_jwk_client = PyJWKClient(_jwks_url) #the PyJWKClient look all the keys from the url and save them

#DTO of the user from the token, not the DB
@dataclass(slots=True, frozen=True)
class AuthenticatedUser:
    auth_id:str
    email:str

# this function is executed every time an endpoint need it. Validate the JWT
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> AuthenticatedUser:
    #get the whole JWT token (with the header,payload and signaturw)
    token=credentials.credentials

    try:
        #read the header to find the kid of the key used to sign the token, then get the public key from the url
        signing_key= _jwk_client.get_signing_key_from_jwt(token)

        # verify the token to validate the signature and check the validity of the token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated"
        )

    except(jwt.PyJWTError, PyJWKClientError) as exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exception


    # get the identity of the user in the SUPABASE AUTH, not the DB. Who's the owner of the token
    auth_id = payload.get("sub") # sub is the ID of supabase auth
    if auth_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'sub' claim. The token doesn't have the identity of the user"
        )

    email = payload.get("email")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'email' claim."
        )

    return AuthenticatedUser(auth_id=auth_id, email=email) # the request is from this user