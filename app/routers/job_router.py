from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..db import database
from ..schemas import schemas
from ..services import auth_service
from ..models import User,JobDescription
from fastapi import HTTPException


router = APIRouter(prefix="/job", tags=["job"])

@router.post("/")
def create_job(
    job: schemas.JobCreateSchema,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
):
    new_job = JobDescription(
        title=job.title,
        description=job.description,
        user_id=current_user.id
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return {
        "id": new_job.id,
        "title": new_job.title
    }

@router.get("/my-jobs")
def get_jobs(
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
):
    jobs = db.query(JobDescription).filter(
        JobDescription.user_id == current_user.id
    ).all()

    return [
        {
            "id": job.id,
            "title": job.title,
            "createdAt": job.createdAt
        }
        for job in jobs
    ]

@router.get("/{job_id}")
def get_job(
    job_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
):
    job = db.query(JobDescription).filter(
        JobDescription.id == job_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "createdAt": job.createdAt
    }

@router.delete("/{job_id}")
def delete_job(
    job_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
):
    job = db.query(JobDescription).filter(
        JobDescription.id == job_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    db.delete(job)
    db.commit()

    return {"msg": "Job deleted successfully"}

