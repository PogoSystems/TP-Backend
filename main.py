from dotenv import load_dotenv
from fastapi import FastAPI

# search .env file in the project
load_dotenv()
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "fast api funca"}
