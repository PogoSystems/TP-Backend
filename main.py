import os

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from modules.course_management.api import router as course_router
from modules.content_processing.api import router as document_router
from modules.quiz_generation.api import router as quiz_router
from modules.iam.api import router as auth_router
from modules.quiz_management.api import router as quiz_management_router
from modules.analytics.api import router as analytics_router
from modules.gamification.api import router as gamification_router
# search .env file in the project
load_dotenv()

app = FastAPI(
    title="TP-Backend — Plataforma de Aprendizaje Inteligente",
    description="API para la gestión de cursos, quizzes y analíticas de aprendizaje.",
    version="1.0.0",
)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url,"http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(course_router, prefix="/api/v1")


app.include_router(document_router, prefix="/api/v1")

app.include_router(auth_router, prefix="/api/v1")

app.include_router(quiz_router, prefix="/api/v1")

app.include_router(quiz_management_router, prefix="/api/v1")

app.include_router(analytics_router, prefix="/api/v1")

app.include_router(gamification_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "fast api funca"}

