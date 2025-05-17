# agents2.py
import requests
import json
import os

# Assuming helper functions might be moved to a shared utility or OPENAI_API_KEY is loaded here too
# For this example, we'll re-define simplified call logic or you can import from agents.py
# from agents import _call_openai_api, _call_deepseek_api, get_llm_response_content # Ideal case

OPENAI_API_KEY = os.getenv("API-KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
DEEPSEEK_COMPLETIONS_URL = "https://api.deepseek.com/v1/chat/completions" # Placeholder

# --- Start Duplicated/Simplified Helper Functions (Ideally import from a shared util or agents.py) ---
def _call_llm_api(messages, model_name, temperature=0.7):
    if model_name.startswith("gpt"):
        if not OPENAI_API_KEY: return {"error": "OpenAI API key not found."}
        api_key = OPENAI_API_KEY
        url = OPENAI_COMPLETIONS_URL
    elif model_name.startswith("deepseek"):
        if not DEEPSEEK_API_KEY: return {"error": "DeepSeek API key not found."}
        api_key = DEEPSEEK_API_KEY
        url = DEEPSEEK_COMPLETIONS_URL # Placeholder
    else:
        return {"error": f"Unsupported model prefix for API call: {model_name}"}

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model_name, "messages": messages, "temperature": temperature}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed for {model_name}: {str(e)}"}

def _get_llm_content(result, model_name):
    if "error" in result: return result
    try:
        # This part needs to be robust for different model response structures
        return result['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        return {"error": f"Failed to parse content from {model_name} response."}
# --- End Duplicated/Simplified Helper Functions ---


def extract_search_string(content):
    """Extracts a plausible search string from the LLM's output."""
    # This heuristic might need improvement. It looks for lines with common search operators.
    # A more robust method might be to instruct the LLM to format the search string clearly.
    lines = content.split('\n')
    for line in lines:
        # Remove common conversational prefixes and numbering
        cleaned_line = line.replace("1. ", "").replace("2. ", "").strip()
        if cleaned_line.startswith('"') and cleaned_line.endswith('"'): # Prioritize fully quoted strings
            return cleaned_line
        if any(op in cleaned_line.upper() for op in [' AND ', ' OR ', ' NOT ']) and len(cleaned_line) > 10: # Heuristic
            return cleaned_line
    # Fallback: return the first non-empty line if specific patterns aren't found, or the whole content
    return lines[0].strip() if lines and lines[0].strip() else content


def generate_search_string_llm(objective, research_questions, model_name="gpt-3.5-turbo"):
    combined_prompt = (f"Given the research objective: '{objective}', and the following research questions: "
                       f"{', '.join(research_questions)}, generate one concise and effective search string "
                       f"for identifying relevant literature for a systematic literature review. "
                       f"The search string should use appropriate keywords and boolean operators (like AND, OR). "
                       f"Provide only the search string itself without any extra explanation or numbering.")
    messages = [
        {"role": "system", "content": "You are a helpful assistant that generates academic search strings."},
        {"role": "user", "content": combined_prompt}
    ]
    
    result_json = _call_llm_api(messages, model_name) # Using the simplified local helper
    
    content = _get_llm_content(result_json, model_name) # Using the simplified local helper
    if isinstance(content, dict) and "error" in content:
        return content # Error dictionary

    search_string = extract_search_string(content)
    # Further clean up: remove potential numbering like "1. " or leading/trailing quotes if not part of a phrase
    search_string = search_string.strip()
    if search_string.startswith("1. "): search_string = search_string[3:]
    if search_string.startswith("2. "): search_string = search_string[3:]
    # Be cautious with stripping quotes if they are intentional for phrase searching
    # if search_string.startswith('"') and search_string.endswith('"'):
    #     search_string = search_string[1:-1] 
    return search_string.strip()

