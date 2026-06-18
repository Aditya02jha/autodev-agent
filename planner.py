import os

from langchain_google_genai import ChatGoogleGenerativeAI

from brain import get_context
from models import ChangePlan


def create_plan(ticket_description):

    context = get_context(ticket_description)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0
    )

    structured_llm = llm.with_structured_output(ChangePlan)

    prompt = f"""
    You are a senior software architect.

    Analyze the repository context.

    Determine:

    1. Which files need modification.
    2. Why each file must change.
    3. High level implementation plan.

    CONTEXT:
    {context}

    TICKET:
    {ticket_description}
    """

    return structured_llm.invoke(prompt)