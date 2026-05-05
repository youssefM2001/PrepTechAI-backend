from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..db import database
from ..schemas import schemas
from ..services import auth_service,ai_service
from ..models import User,JobDescription,Interview,CV,InterviewMessage
from fastapi import HTTPException
import json


router = APIRouter(prefix="/interview", tags=["interview"])


@router.post('/')
def interview(
    request : schemas.InterviewRequest,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db),
):
    cv = db.query(CV).filter(
        CV.id == request.cv_id,
        CV.user_id == current_user.id
    ).first()

    job_description = db.query(JobDescription).filter(
        JobDescription.id == request.job_description_id,
        JobDescription.user_id == current_user.id 
        ).first()

    if not cv or not job_description:
        raise HTTPException(status_code=404,detail='job description or cv not found')
    
    if request.type not in ['HR','TECHNICAL']:
        raise HTTPException(status_code=400, detail="Invalid type")
    if request.difficulty not in ['easy','medium','hard']:
        raise HTTPException(status_code=400, detail="Invalid difficulty")
    if request.total_questions<=0 or request.total_questions>20:
        raise HTTPException(status_code=400, detail="Invalid number")
    
    formatted_cv = ai_service.prepare_cv_for_ai(cv.content)
    


    interview = Interview(
        user_id = current_user.id,
        cv_id = cv.id,
        job_description_id = job_description.id,
        type = request.type,
        difficulty = request.difficulty,
        total_questions = request.total_questions,
        cv_summary=formatted_cv
    )

    db.add(interview)
    db.commit()
    db.refresh(interview)

    job_description_content = job_description.description


    try:
        first_question = ai_service.generate_first_question(
            formatted_cv, job_description_content,request.difficulty,request.type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    interviewMessage = InterviewMessage(
        interview_id = interview.id,
        role = 'ai',
        content = first_question,
    )

    db.add(interviewMessage)

    interview.current_question_index = 1

    db.commit()


    return {
        "interview_id": interview.id,
        "question": first_question
    }    


@router.post('/{interview_id}/next')
def next_question(
    interview_id: int,
    answer: str,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
):
    interview = db.query(Interview).filter(
        Interview.id == interview_id
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail='interview not found')

    if interview.user_id != current_user.id:
        raise HTTPException(status_code=403, detail='unauthorized access')

    if interview.is_finished:
        return {"message": "Interview already completed"}

    # 🔹 Get last AI question
    last_question = db.query(InterviewMessage).filter(
        InterviewMessage.interview_id == interview.id,
        InterviewMessage.role == "ai"
    ).order_by(InterviewMessage.id.desc()).first()

    if not last_question:
        raise HTTPException(status_code=400, detail="No question found")

    # 🔹 Save user answer
    user_msg = InterviewMessage(
        interview_id=interview.id,
        role="user",
        content=answer
    )
    db.add(user_msg)

    # 🔹 Evaluate answer (NEW STRUCTURE)
    evaluation = ai_service.evaluate_answer(
        last_question.content,
        answer
    )

    # 🔹 Load previous results
    if interview.result_json:
        if isinstance(interview.result_json, str):
            try:
                result_data = json.loads(interview.result_json)
            except json.JSONDecodeError:
                result_data = {"answers": []}
        else:
            result_data = interview.result_json
    else:
        result_data = {"answers": []}

    if "answers" not in result_data:
        result_data["answers"] = []

    # 🔹 Store full evaluation (memory)
    result_data["answers"].append({
        "question": last_question.content,
        "answer": answer,
        "feedback": evaluation.get("feedback"),
        "score": evaluation.get("score"),
        "strengths": evaluation.get("strengths", []),
        "weaknesses": evaluation.get("weaknesses", []),
        "next_focus": evaluation.get("next_focus"),
        "type": getattr(last_question, "message_type", "theory")  # 👈 important
    })

    interview.result_json = json.dumps(result_data)
    db.commit()

    if interview.current_question_index >= interview.total_questions:

        report = ai_service.generate_final_report(result_data)

        interview.final_score = report["final_score"]
        result_data["summary"] = report

        interview.result_json = json.dumps(result_data)
        interview.is_finished = True

        db.commit()

        return {
            "message": "Interview completed",
            "report": report
        }

    # 🔹 Load last messages (limit for context)
    messages = db.query(InterviewMessage)\
        .filter(InterviewMessage.interview_id == interview.id)\
        .order_by(InterviewMessage.id.desc())\
        .limit(10)\
        .all()[::-1]

    history = [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]

    cv = db.query(CV).filter(CV.id == interview.cv_id).first()
    job = db.query(JobDescription).filter(JobDescription.id == interview.job_description_id).first()

    formatted_cv = interview.cv_summary

    # 🔹 Generate next question (NOW RETURNS JSON)
    result = ai_service.generate_next_question(
        formatted_cv,
        job.description,
        history,
        result_data,
        interview.difficulty,
        interview.type
    )

    next_q = result["question"]
    q_type = result["type"]

    # 🔹 Store AI question WITH TYPE
    ai_msg = InterviewMessage(
        interview_id=interview.id,
        role="ai",
        content=next_q,
        message_type=q_type   # 👈 CRUCIAL
    )

    db.add(ai_msg)

    interview.current_question_index += 1
    db.commit()

    return {
        "question": next_q,
        "type": q_type,  # 👈 optional (useful for frontend)
        "current": interview.current_question_index,
        "total": interview.total_questions
    }


@router.get('/{interview_id}/result')
def get_interview_result(
    interview_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
):
    interview = db.query(Interview).filter(
        Interview.id == interview_id
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if not interview.is_finished:
        raise HTTPException(status_code=400, detail="Interview not finished yet")

    # ✅ Parse result_json if it's a string
    if interview.result_json:
        if isinstance(interview.result_json, str):
            try:
                result_data = json.loads(interview.result_json)
            except json.JSONDecodeError:
                result_data = {"answers": [], "summary": {}}
        else:
            result_data = interview.result_json
    else:
        result_data = {"answers": [], "summary": {}}

    return {
        "interview_id": interview.id,
        "final_score": interview.final_score,
        "summary": result_data.get("summary", {}),
        "answers": result_data.get("answers", [])
    }


@router.get('/my')
def get_my_interviews(
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(database.get_db)
):
    interviews = db.query(Interview).filter(
        Interview.user_id == current_user.id
    ).order_by(Interview.id.desc()).all()

    return [
        {
            "id": interview.id,
            "type": interview.type,
            "difficulty": interview.difficulty,
            "total_questions": interview.total_questions,
            "current_question_index": interview.current_question_index,
            "is_finished": interview.is_finished,
            "final_score": interview.final_score,
            "created_at": interview.created_at
        }
        for interview in interviews
    ]
