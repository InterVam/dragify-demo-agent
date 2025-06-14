import os
from langchain_groq import ChatGroq

def get_llm():
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is not set")
    return ChatGroq(
        model="llama3-70b-8192",
        temperature=0,
        groq_api_key=groq_api_key,
        max_tokens=3000,
        timeout=None,
        max_retries=3,
    )
