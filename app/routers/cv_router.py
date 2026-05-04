from fastapi import APIRouter,UploadFile,File,Depends,HTTPException
from sqlalchemy.orm import Session
from ..models import CV,User
from ..db import database
from ..services import auth_service
import os
import shutil
import pdfplumber
import re


router = APIRouter(prefix="/cv",tags=["cv"])

UPLOAD_DIR = "uploads/cvs"

@router.post('/upload')
def upload(
        file : UploadFile = File(...),
        current_user : User = Depends(auth_service.get_current_user),
        db: Session = Depends(database.get_db)
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    file_name = f"{current_user.id}_{file.filename}"
    
    file_path = os.path.join(UPLOAD_DIR,file_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    full_text = "" 
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
    except Exception:
        raise HTTPException(status_code=400, detail="Error reading PDF")
    
    if not full_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    
    new_cv = CV(
        user_id = current_user.id,
        file_path = file_path,
        content = clean_text(full_text),
        file_name = file.filename
    )

    db.add(new_cv)
    db.commit()
    db.refresh(new_cv)


    return {
        "msg": "CV uploaded and processed",
        "cv_id": new_cv.id
    }


@router.get("/my-cvs")
def get_user_cvs(
    current_user : User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
    ):

    my_cvs = db.query(CV).filter(CV.user_id == current_user.id).all()

    return [
        {
            'id' : cv.id,
            'filename' : cv.file_name,
            'created_at' : cv.created_at
        }
        for cv in my_cvs
    ]
    

@router.get("/my-cvs/{cv_id}")
def get_cv(
    cv_id : int,
    current_user : User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
    ):
    cv = db.query(CV).filter(CV.id == cv_id).first()

    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    

    if cv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return {
            'id' : cv.id,
            'filename' : cv.file_name,
            'created_at' : cv.created_at
        }
@router.delete('/delete/{cv_id}')
def delete_cv(
    cv_id : int,
    current_user : User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
):
    cv = db.query(CV).filter(CV.id == cv_id).first()

    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    if cv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if os.path.exists(cv.file_path):
        os.remove(cv.file_path)

    db.delete(cv)
    db.commit()

    return {"msg": "CV deleted successfully"}


from fastapi.responses import FileResponse

@router.get("/{cv_id}/download")
def download_cv(
    cv_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
):

    cv = db.query(CV).filter(CV.id == cv_id).first()

    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    if cv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if not os.path.isfile(cv.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=cv.file_path,
        filename=cv.file_name,
        media_type='application/pdf'
    )

def clean_text(text: str) -> str:
    if not text:
        return text
    
    # remove null bytes only (critical)
    text = text.replace("\x00", "")

    # remove problematic control chars but KEEP newlines
    text = re.sub(r"[\x01-\x09\x0B-\x1F\x7F]", "", text)

    return text.strip()

