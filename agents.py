# agents.py
import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
import requests
from flask import jsonify  # Keep for existing error responses

# Load environment variables from .env file in the same directory as this file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Get API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Debug print to verify keys are loaded
print(f"[AGENTS.PY] OPENAI_API_KEY loaded: {'Yes' if OPENAI_API_KEY else 'No'}")
print(f"[AGENTS.PY] DEEPSEEK_API_KEY loaded: {'Yes' if DEEPSEEK_API_KEY else 'No'}")

# API Endpoints
OPENAI_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
# !!! IMPORTANT: Replace with the actual DeepSeek API endpoint !!!
DEEPSEEK_COMPLETIONS_URL = "https://api.deepseek.com/v1/chat/completions" # Placeholder

def _call_openai_api(messages, model_name, temperature=0.7, max_tokens=None):
    """Helper function to call OpenAI API."""
    if not OPENAI_API_KEY:
        return {"error": "OpenAI API key not found."}
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
    
    try:
        response = requests.post(OPENAI_COMPLETIONS_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()  # Raises an exception for HTTP error codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"OpenAI API request failed: {e}")
        return {"error": f"OpenAI API request failed: {str(e)}"}

def _call_deepseek_api(messages, model_name, temperature=0.7, max_tokens=None):
    """Helper function to call DeepSeek API."""
    # !!! IMPORTANT: This is a placeholder. Adapt to DeepSeek's actual API. !!!
    # You'll need to verify the model_name, payload structure, and endpoint.
    if not DEEPSEEK_API_KEY:
        return {"error": "DeepSeek API key not found."}
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}", # Or other auth mechanism
        "Content-Type": "application/json"
    }
    # Hypothetical payload structure for DeepSeek - ADJUST AS NEEDED
    payload = {
        "model": model_name, # This might be part of the URL or a specific payload parameter
        "messages": messages, # Ensure this message format is what DeepSeek expects
        "temperature": temperature,
        # "max_tokens": max_tokens, # Check if DeepSeek supports this
    }
    if max_tokens: # Add if supported
        payload["max_tokens"] = max_tokens

    try:
        response = requests.post(DEEPSEEK_COMPLETIONS_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        # !!! IMPORTANT: DeepSeek's response structure might differ from OpenAI's.
        # You may need to adapt how you extract 'content' below.
        # For example, it might not be ['choices'][0]['message']['content']
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"DeepSeek API request failed: {e}")
        return {"error": f"DeepSeek API request failed: {str(e)}"}

def get_llm_response_content(result, model_name):
    """Extracts content from LLM response, handling potential differences."""
    if "error" in result:
        return result # Propagate error

    try:
        # Standard OpenAI structure
        if model_name.startswith("gpt"):
            return result['choices'][0]['message']['content']
        # Placeholder for DeepSeek - adjust based on their actual response
        elif model_name.startswith("deepseek"):
            # Example: You might need to access result['data']['choices'][0]['content'] or similar
            # This is a common alternative structure. CONSULT DEEPSEEK DOCS.
            if 'choices' in result and result['choices'] and 'message' in result['choices'][0] and 'content' in result['choices'][0]['message']:
                 return result['choices'][0]['message']['content']
            # Add other potential structures for DeepSeek if necessary
            else:
                print(f"Unexpected response structure from DeepSeek: {result}")
                return {"error": "Failed to parse response from DeepSeek due to unexpected structure."}
        else:
            return {"error": f"Content extraction not implemented for model: {model_name}"}
    except (KeyError, IndexError, TypeError) as e:
        print(f"Failed to parse content from {model_name} response: {e}. Response: {result}")
        return {"error": f"Failed to parse content from {model_name} response."}


def generate_research_questions_and_purpose(objective, num_questions, model_name="gpt-3.5-turbo"):
    prompt_content = (f"You are a helpful assistant capable of generating research questions along with their purposes "
                      f"for a systematic literature review.\n"
                      f"Given the research objective: '{objective}', generate {num_questions} distinct research questions, "
                      f"each followed by its specific purpose. Start purpose with 'Purpose: To examine', or 'Purpose: To investigate'.")
    messages = [
        {"role": "system", "content": "You are a helpful assistant capable of generating research questions along with their purposes for a systematic literature review."},
        {"role": "user", "content": prompt_content}
    ]

    result_json = {}
    if model_name.startswith("gpt"):
        result_json = _call_openai_api(messages, model_name)
    elif model_name.startswith("deepseek"):
        result_json = _call_deepseek_api(messages, model_name)
    else:
        return {"error": f"Unsupported model: {model_name}"}

    content = get_llm_response_content(result_json, model_name)
    if isinstance(content, dict) and "error" in content: # Check if get_llm_response_content returned an error
        return content

    lines = [line for line in content.strip().split('\n') if line.strip()]
    
    question_purpose_objects = []
    current_question = None
    for line in lines:
        line_lower = line.lower()
        # Try to identify question lines (heuristic, might need refinement)
        if not line_lower.startswith("purpose:") and ("?" in line or len(question_purpose_objects) == 0 or (current_question is not None and "purpose:" not in lines[lines.index(line)-1].lower() if lines.index(line)>0 else True)):
            # Remove "Research Question X:" prefix
            current_question = re.sub(r"^(research question\s*\d*:?\s*)+", "", line, flags=re.IGNORECASE).strip()
        elif line_lower.startswith("purpose:") and current_question:
            purpose = line.replace("Purpose:", "").strip()
            question_purpose_objects.append({"question": current_question, "purpose": purpose})
            current_question = None # Reset for the next pair
    
    # If parsing failed to create pairs, try a simpler split (less robust)
    if not question_purpose_objects and len(lines) >= num_questions * 2 :
        for i in range(0, min(len(lines), num_questions * 2), 2):
            question = re.sub(r"^(research question\s*\d*:?\s*)+", "", lines[i], flags=re.IGNORECASE).strip()
            purpose = lines[i+1].replace("Purpose:", "").strip() if (i+1 < len(lines)) else "Purpose not provided"
            question_purpose_objects.append({"question": question, "purpose": purpose})
            
    if not question_purpose_objects:
        return {"error": f"Could not parse questions and purposes from model {model_name}'s response. Response: {content}"}

    return {"research_questions": question_purpose_objects[:num_questions]}


def generate_summary_llm(prompt, model_name="gpt-3.5-turbo"):
    """Generates a summary using the specified LLM based on the provided prompt."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    
    result_json = {}
    if model_name.startswith("gpt"):
        result_json = _call_openai_api(messages, model_name)
    elif model_name.startswith("deepseek"):
        result_json = _call_deepseek_api(messages, model_name)
    else:
        return {"error": f"Unsupported model: {model_name}"}

    content = get_llm_response_content(result_json, model_name)
    if isinstance(content, dict) and "error" in content:
        return content
    return content.strip()

def generate_abstract_llm(prompt, model_name="gpt-3.5-turbo"):
    """Generates a summary abstract using the specified LLM."""
    return generate_summary_llm(prompt, model_name)

def generate_introduction_summary_llm(prompt, model_name="gpt-3.5-turbo"):
    """Generates an introduction summary using the specified LLM."""
    return generate_summary_llm(prompt, model_name)

def generate_summary_conclusion_llm(papers_info, model_name="gpt-3.5-turbo"):
    """Generates a conclusion summary from papers_info using the specified LLM."""
    prompt_parts = ["Summarize the conclusions of the following papers:"]
    for paper in papers_info:
        title = paper.get("title", "N/A")
        author = paper.get("creator", "N/A") # Assuming 'creator' holds author info
        year = paper.get("year", "N/A")
        prompt_parts.append(f"- '{title}' by {author} ({year})")
    prompt = " ".join(prompt_parts)
    
    return generate_summary_llm(prompt, model_name)

