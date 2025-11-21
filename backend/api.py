from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


from .storage import (
    load_prompts,
    save_prompts,
    load_inbox,
    EMAILS,
    PROCESSED_EMAILS,
    DRAFTS,
)

import json

app = FastAPI(title="Email Productivity Agent")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




class PromptConfig(BaseModel):
    categorization_prompt: str
    action_item_prompt: str
    auto_reply_prompt: str


class AgentQuery(BaseModel):
    email_id: Optional[int] = None
    user_query: str


class DraftRequest(BaseModel):
    email_id: Optional[int] = None  # if replying
    tone: str = "formal"
    additional_instructions: Optional[str] = None




def llm_call(system_prompt, user_content, model="llama-3.1-8b-instant"):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    )
    return response.choices[0].message.content


#Routes#

@app.get("/prompts", response_model=PromptConfig)
def get_prompts():
    prompts = load_prompts()
    return PromptConfig(**prompts)


@app.post("/prompts", response_model=PromptConfig)
def update_prompts(config: PromptConfig):
    save_prompts(config.dict())
    return config


@app.post("/inbox/load")
def load_and_process_inbox():
    global EMAILS, PROCESSED_EMAILS

    prompts = load_prompts()
    if not prompts.get("categorization_prompt") or not prompts.get("action_item_prompt"):
        raise HTTPException(status_code=400, detail="Prompts not configured")

    EMAILS.clear()
    PROCESSED_EMAILS.clear()

    EMAILS = load_inbox()

    for email in EMAILS:
        email_id = email["id"]
        content = f"Subject: {email['subject']}\n\nBody:\n{email['body']}"

        # Categorization
        cat_response = llm_call(prompts["categorization_prompt"], content)
        try:
            cat_json = json.loads(cat_response)
        except json.JSONDecodeError:
            cat_json = {"category": "Unknown", "reason": "Failed to parse LLM output"}

        # Action items
        act_response = llm_call(prompts["action_item_prompt"], content)
        try:
            act_json = json.loads(act_response)
        except json.JSONDecodeError:
            act_json = []

        PROCESSED_EMAILS[email_id] = {
            "category": cat_json.get("category", "Unknown"),
            "category_reason": cat_json.get("reason", ""),
            "actions": act_json
        }

    return {
        "status": "ok",
        "processed_count": len(EMAILS)
    }


@app.get("/emails")
def list_emails():
    result = []
    for email in EMAILS:
        processed = PROCESSED_EMAILS.get(email["id"], {})
        result.append({
            "id": email["id"],
            "sender": email["sender"],
            "subject": email["subject"],
            "timestamp": email["timestamp"],
            "category": processed.get("category", "Not processed")
        })
    return result


@app.get("/emails/{email_id}")
def get_email(email_id: int):
    email = next((e for e in EMAILS if e["id"] == email_id), None)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    processed = PROCESSED_EMAILS.get(email_id, {})
    return {
        "email": email,
        "processed": processed
    }


@app.post("/agent/query")
def agent_query(payload: AgentQuery):
    prompts = load_prompts()  

    email_text = ""
    if payload.email_id is not None:
        email = next((e for e in EMAILS if e["id"] == payload.email_id), None)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        email_text = f"Subject: {email['subject']}\n\nBody:\n{email['body']}\n\n"

    
    system_prompt = """
You are an intelligent Email Productivity Agent.

You are given:
1) An email (subject + body)
2) A user question or instruction

Your job:
- If the user asks for a SUMMARY → give a clear, concise summary.
- If the user asks for TASKS / ACTION ITEMS → list them clearly.
- If the user asks to DRAFT / WRITE A REPLY → write a good reply email.
- If the user asks about URGENT / IMPORTANT emails → reason from the content and explain.
- If the request is something else, respond in the most helpful way using the email contents.

Always directly answer the user's question in a clean, readable format.
Do NOT ask the user what they want; infer it from their question.
    """.strip()

    combined_content = f"EMAIL:\n{email_text}\n\nUSER REQUEST:\n{payload.user_query}"

    response_text = llm_call(system_prompt, combined_content)

    return {"response": response_text}


@app.post("/drafts")
def create_draft(payload: DraftRequest):
    prompts = load_prompts()

    email_context = ""
    if payload.email_id is not None:
        email = next((e for e in EMAILS if e["id"] == payload.email_id), None)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        email_context = f"Original email:\nSubject: {email['subject']}\n\n{email['body']}\n\n"

    content = (
        f"{email_context}"
        f"Tone: {payload.tone}\n"
        f"Additional instructions: {payload.additional_instructions or 'None'}"
    )

    result = llm_call(prompts["auto_reply_prompt"], content)

    try:
        draft_json = json.loads(result)
    except json.JSONDecodeError:
        draft_json = {
            "subject": "Re: (draft)",
            "body": result,
            "suggested_follow_ups": []
        }

    draft_record = {
        "id": len(DRAFTS) + 1,
        "email_id": payload.email_id,
        "subject": draft_json.get("subject"),
        "body": draft_json.get("body"),
        "suggested_follow_ups": draft_json.get("suggested_follow_ups", [])
    }
    DRAFTS.append(draft_record)

    return draft_record


@app.get("/drafts")
def list_drafts():
    return DRAFTS
