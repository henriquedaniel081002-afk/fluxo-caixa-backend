from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional
from dotenv import load_dotenv
import os
import json

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
APP_PASSWORD = os.getenv("APP_PASSWORD")

if not DATABASE_URL or not APP_PASSWORD:
    raise RuntimeError("DATABASE_URL ou APP_PASSWORD não configurados")

engine = create_engine(DATABASE_URL, echo=False)

class AppState(SQLModel, table=True):
    id: Optional[int] = Field(default=1, primary_key=True)
    data: str  # JSON com initialBalance e transactions

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_session():
    with Session(engine) as session:
        yield session

def check_password(x_app_password: str = Header(...)):
    if x_app_password != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Senha inválida")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        existing = session.exec(select(AppState)).first()
        if not existing:
            empty_data = json.dumps({
                "initialBalance": 0,
                "transactions": []
            })
            session.add(AppState(data=empty_data))
            session.commit()

@app.get("/data", dependencies=[Depends(check_password)])
def get_data(session: Session = Depends(get_session)):
    row = session.exec(select(AppState)).first()
    return json.loads(row.data)

@app.put("/data", dependencies=[Depends(check_password)])
def save_data(payload: dict, session: Session = Depends(get_session)):
    row = session.exec(select(AppState)).first()
    row.data = json.dumps(payload)
    session.add(row)
    session.commit()
    return {"ok": True}
@app.get("/ping")
def ping():
    return {"pong": True}

