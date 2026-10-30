
import os
import datetime as datetime_lib
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.database import (
    SessionLocal,
    TutorConversation,
    TutorMessage,
    subject,
    study_log
)

load_dotenv()

MODEL_NAME = "gemini-3.6-flash"


def get_tutor_model():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found.")

    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=api_key
    )


def create_conversation(user_id, subject_id=None,
                       study_log_id=None, learning_mode="Doubt Solving"):

    db = SessionLocal()

    try:
        if study_log_id is not None:
            log = db.query(study_log).filter(
                study_log.id == study_log_id,
                study_log.user_id == user_id
            ).first()

            if not log:
                raise ValueError("Study log not found.")

            subject_id = log.subject_id

        conversation = TutorConversation(
            user_id=user_id,
            subject_id=subject_id,
            study_log_id=study_log_id,
            learning_mode=learning_mode,
            title="New Conversation"
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        return conversation.id

    finally:
        db.close()


def get_user_conversations(user_id):
    db = SessionLocal()

    try:
        return db.query(TutorConversation).filter(
            TutorConversation.user_id == user_id
        ).order_by(
            TutorConversation.updated_at.desc()
        ).all()

    finally:
        db.close()


def get_conversation_history(user_id, conversation_id):
    db = SessionLocal()

    try:
        conversation = db.query(TutorConversation).filter(
            TutorConversation.id == conversation_id,
            TutorConversation.user_id == user_id
        ).first()

        if not conversation:
            return []

        messages = db.query(TutorMessage).filter(
            TutorMessage.conversation_id == conversation_id
        ).order_by(TutorMessage.id).all()

        return [
            {"role": message.role, "content": message.content}
            for message in messages
        ]

    finally:
        db.close()


def generate_tutor_response(user_id, conversation_id, user_message):

    db = SessionLocal()

    try:
        conversation = db.query(TutorConversation).filter(
            TutorConversation.id == conversation_id,
            TutorConversation.user_id == user_id
        ).first()

        if not conversation:
            raise ValueError("Conversation not found.")

        subject_name = "General Learning"

        if conversation.subject_id:
            sub = db.query(subject).filter(
                subject.id == conversation.subject_id
            ).first()

            if sub:
                subject_name = sub.name

        study_context = ""

        if conversation.study_log_id:
            log = db.query(study_log).filter(
                study_log.id == conversation.study_log_id,
                study_log.user_id == user_id
            ).first()

            if log:
                study_context = log.notes or ""

        previous_messages = db.query(TutorMessage).filter(
            TutorMessage.conversation_id == conversation_id
        ).order_by(TutorMessage.id).all()

        history = []

        for message in previous_messages:
            if message.role == "user":
                history.append(HumanMessage(content=message.content))
            else:
                history.append(AIMessage(content=message.content))

        system_prompt = f"""
        You are an AI Tutor in a Smart Learning Planner application.

        Student's subject: {subject_name}
        Learning mode: {conversation.learning_mode}

        Study log context:
        {study_context}

        Explain concepts clearly and accurately.
        Use simple examples where useful.
        Answer follow-up questions using the conversation history.
        Keep answers reasonably concise and suitable for an engineering student.
        Do not invent student progress or exam dates.
        """

        messages = [
            SystemMessage(content=system_prompt)
        ] + history + [
            HumanMessage(content=user_message)
        ]

        model = get_tutor_model()
        response = model.invoke(messages)

        if isinstance(response.content, str):
            ai_response = response.content

        elif isinstance(response.content, list):
            ai_response = "\n".join(
                block.get("text", "")
                for block in response.content
                if isinstance(block, dict) and block.get("type") == "text"
            ).strip()

        else:
            ai_response = str(response.content)

        # Save both messages after successful generation
        user_msg = TutorMessage(
            conversation_id=conversation_id,
            role="user",
            content=user_message
        )

        ai_msg = TutorMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response
        )

        db.add(user_msg)
        db.add(ai_msg)

        # Use first question as conversation title
        if conversation.title == "New Conversation":
            conversation.title = user_message[:60]

        conversation.updated_at = datetime_lib.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        db.commit()

        return ai_response

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def get_or_create_log_conversation(user_id, study_log_id):
    db = SessionLocal()

    try:
        # Check whether this log already has a tutor conversation
        log = db.query(study_log).filter(
            study_log.id == study_log_id,
            study_log.user_id == user_id
        ).first()

        if not log:
            raise ValueError("Study log not found.")

        conversation = db.query(TutorConversation).filter(
            TutorConversation.user_id == user_id,
            TutorConversation.study_log_id == study_log_id
        ).first()

        if conversation:
            return conversation.id

        # Create a new conversation linked to this study log
        conversation = TutorConversation(
            user_id=user_id,
            subject_id=log.subject_id,
            study_log_id=study_log_id,
            learning_mode="Doubt Solving",
            title="Study Log Discussion"
        )

        db.add(conversation)
        db.flush()

        # Migrate any existing chat history from the old JSON field
        if log.ai_chat_history:
            try:
                old_history = json.loads(log.ai_chat_history)

                if isinstance(old_history, list):
                    for message in old_history:
                        if not isinstance(message, dict):
                            continue

                        role = message.get("role")
                        content = message.get("content")

                        if role in ["user", "assistant"] and content:
                            db.add(TutorMessage(
                                conversation_id=conversation.id,
                                role=role,
                                content=str(content)
                            ))

            except (json.JSONDecodeError, TypeError):
                pass

        db.commit()
        return conversation.id

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def save_tutor_exchange(user_id, conversation_id, user_message, ai_response):

    db = SessionLocal()

    try:
        conversation = db.query(TutorConversation).filter(
            TutorConversation.id == conversation_id,
            TutorConversation.user_id == user_id
        ).first()

        if not conversation:
            raise ValueError("Conversation not found.")

        db.add(TutorMessage(
            conversation_id=conversation_id,
            role="user",
            content=user_message
        ))

        db.add(TutorMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response
        ))

        if conversation.title == "New Conversation":
            conversation.title = user_message[:60]

        conversation.updated_at = datetime_lib.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
