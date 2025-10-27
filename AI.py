import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TEST = os.getenv("TEST")

genai.configure(api_key=GEMINI_API_KEY)

def infer(prompt: str, op: str) -> str:
    """
    This function takes a prompt as input and returns the AI-generated output.
    """
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    response = model.generate_content(prompt + op)
    if TEST:
        print(f"[AI] Prompt:\n{prompt + op}")
        print(f"[AI] Response:\n{response.text}")
        print()
    return response.text

