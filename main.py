from dotenv import load_dotenv
from fastapi import FastAPI

from modules.course_management.api import router as course_router
from modules.content_processing.api import router as document_router

# search .env file in the project
load_dotenv()

app = FastAPI(
    title="TP-Backend — Plataforma de Aprendizaje Inteligente",
    description="API para la gestión de cursos, quizzes y analíticas de aprendizaje.",
    version="1.0.0",
)

app.include_router(course_router, prefix="/api/v1")


app.include_router(document_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "fast api funca"}
