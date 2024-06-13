from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    SecurityScopes,
)
from starlette.background import BackgroundTask
from starlette.types import Message
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from typing import Dict, Any
import requests
import logging

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Chains",
        "email": "alicechains@example.com",
        "hashed_password": "$2b$12$gSvqqUPvlXP2tfVFaWK1Be7DlH.PKZbv5H8KnzzVgXXbVxpva.pFm",
        "disabled": True,
    },
}


app = FastAPI()

# oauth2_scheme = OAuth2PasswordBearer(
#     tokenUrl="token",
#     scopes={"me": "Read information about the current user.", "items": "Read items."},
# )

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str

class TokenData(BaseModel):
    username: str = None

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    
def verify_password(plain_password, hashed_password):
    return plain_password == hashed_password

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# not needed when using FastAPI>=0.108.0.
async def set_body(request: Request, body: bytes):
    async def receive() -> Message:
        return {'type': 'http.request', 'body': body}
    request._receive = receive

def log_info(req_body, res_body, req_headers):
    logging.info(f"Content-Typ: {req_headers}")
    logging.info(req_body)
    logging.info(res_body)


@app.middleware('http')
async def some_middleware(request: Request, call_next):
    req_body = await request.body()
    headers = request.headers.get('Content-Type')
    await set_body(request, req_body)  # not needed when using FastAPI>=0.108.0.
    response = await call_next(request)
    
    res_body = b''
    async for chunk in response.body_iterator:
        res_body += chunk
    
    task = BackgroundTask(log_info, req_body, res_body, headers)
    return Response(content=res_body, status_code=response.status_code, 
        headers=dict(response.headers), media_type=response.media_type, background=task)


@app.post("/token")
async def login(
    # request: Request, form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request,
    form_data: Dict[Any, Any],
):
    # print(form_data)
    # {'scope': None, 'audience': None, 'username': None, 'password': None, 'grant_type': 'password', 'client_id': ['johndoe'], 'client_secret': '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'}
    content_type = request.headers.get('Content-Type')
    print(f"Content-Type: {content_type}")
    client_id = form_data['client_id'][0]
    client_secret = form_data['client_secret']
    user = authenticate_user(fake_users_db, client_id, client_secret)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/thageesan/webhook")
async def webhook_endpoint(
    # token: str = Depends(oauth2_scheme)
    # token
    request: Request,
    ):
    # Here you would process the webhook payload
    content_type = request.headers.get('Content-Type')
    print(f"Content-Type: {content_type}")
    print("Webhook received!")
    return {"message": "Webhook received successfully"}

@app.get("/")
async def webhook_endpoint():
    # Here you would process the webhook payload
    print("Hello World!")
    return {"message": "Hello World!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
