from fastapi import FastAPI
from app.db.database import engine
from app.models.base import Base

from app.models import user, cv, interview, jobDescription,InterviewMessage
from app.routers import auth_router,cv_router,job_router,interview_router


app = FastAPI()

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "API is running 🚀"}


app.include_router(auth_router.router)
app.include_router(cv_router.router)
app.include_router(job_router.router)
app.include_router(interview_router.router)
