from pydantic import BaseModel

class userCreate(BaseModel):
    email:str
    password:str

class JobCreateSchema(BaseModel):
    title: str
    description: str

class InterviewRequest(BaseModel):
    cv_id: int
    job_description_id: int
    type: str
    difficulty: str
    total_questions: int
