# agent4.py
import requests
import os
import re
import json # Added for consistency if needed, though not strictly used in original

# Assuming helper functions might be moved to a shared utility or API keys are loaded here too
# from agents import _call_openai_api, _call_deepseek_api, get_llm_response_content # Ideal case

OPENAI_API_KEY = os.getenv("API-KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
DEEPSEEK_COMPLETIONS_URL = "https://api.deepseek.com/v1/chat/completions" # Placeholder

# --- Start Duplicated/Simplified Helper Functions (Ideally import from a shared util or agents.py) ---
def _call_llm_api_for_agents4(messages, model_name, temperature=0.7, max_tokens=None):
    # This is a simplified version. For production, centralize this logic (e.g., in agents.py or a utils.py)
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
    if max_tokens:
        payload["max_tokens"] = max_tokens
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180) # Increased timeout for potentially longer tasks
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed for {model_name}: {str(e)}"}

def _get_llm_content_for_agents4(result, model_name):
    if "error" in result: return result
    try:
        # This part needs to be robust for different model response structures
        return result['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        return {"error": f"Failed to parse content from {model_name} response."}
# --- End Duplicated/Simplified Helper Functions ---

def check_paper_relevance_llm(title, search_string, model_name="gpt-3.5-turbo"):
    # This function determines relevance. The original name included "keywords" but didn't explicitly extract them.
    # Adjusting prompt for clarity.
    prompt = (f"Determine if the paper titled '{title}' is relevant to the research topic described by "
              f"'{search_string}'. Respond with 'Relevant' or 'Not Relevant' only.")
    messages = [
        {"role": "system", "content": "You are an assistant that determines paper relevance."},
        {"role": "user", "content": prompt}
    ]

    result_json = _call_llm_api_for_agents4(messages, model_name, temperature=0.2) # Lower temp for classification
    
    response_text = _get_llm_content_for_agents4(result_json, model_name)
    if isinstance(response_text, dict) and "error" in response_text:
        print(f"Error checking relevance for '{title}': {response_text['error']}")
        return False # Default to not relevant on error

    print(f"Relevance check for '{title}' with {model_name}: {response_text}")
    if "not relevant" in response_text.lower():
        return False
    elif "relevant" in response_text.lower():
        return True
    else:
        # If the model doesn't give a clear "Relevant" / "Not Relevant"
        print(f"Ambiguous relevance response for '{title}': {response_text}. Defaulting to not relevant.")
        return False


def filter_papers_llm(search_string, papers, model_name="gpt-3.5-turbo"):
    filtered_papers = []
    for paper in papers:
        title = paper.get('title')
        if not title:
            print(f"Paper skipped due to missing title: {paper}")
            continue
        if check_paper_relevance_llm(title, search_string, model_name):
            filtered_papers.append(paper)
    return filtered_papers


def generate_response_llm(question, papers_info, model_name="gpt-4-turbo-preview", max_tokens=512): # Increased default max_tokens
    messages = [{
        "role": "system",
        "content": "You are a knowledgeable assistant who can answer research questions based on provided papers information."
    }]

    # Ensure papers_info is a list of dictionaries
    if not isinstance(papers_info, list):
        papers_info = [] # Or handle error appropriately

    papers_context_parts = []
    for paper in papers_info:
        if isinstance(paper, dict):
            title = paper.get('title', 'N/A')
            creator = paper.get('creator', 'N/A') # Author(s)
            year = paper.get('year', 'N/A')
            # Consider adding abstract if available and relevant for better context
            papers_context_parts.append(f"- Title: '{title}', Author(s): {creator}, Year: {year}.")
        else:
            print(f"Skipping invalid paper entry: {paper}")

    papers_context = "\n".join(papers_context_parts)
    if not papers_context:
        papers_context = "No paper information provided."


    messages.append({
        "role": "system",
        "content": f"Research Question: {question}\n\nPapers Information:\n{papers_context}"
    })
    
    messages.append({
        "role": "user",
        "content": ("Based on the provided papers information, please answer the research question. "
                    "If possible, cite relevant paper titles or authors for cross-verification. "
                    "Provide a comprehensive answer.")
    })
    
    result_json = _call_llm_api_for_agents4(messages, model_name, temperature=0.7, max_tokens=max_tokens)
    
    latest_response = _get_llm_content_for_agents4(result_json, model_name)
    if isinstance(latest_response, dict) and "error" in latest_response:
        return f"An error occurred while generating the response with {model_name}: {latest_response['error']}"
    
    return latest_response

