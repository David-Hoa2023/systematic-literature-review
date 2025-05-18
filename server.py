from dotenv import load_dotenv
import os
import tempfile
from flask import Flask, render_template,send_file, send_from_directory, request, jsonify
import datetime
# Import refactored agent functions
from agents import (
    generate_research_questions_and_purpose,
    generate_abstract_llm,
    generate_introduction_summary_llm,
    generate_summary_conclusion_llm
)
# from agents2 import generate_search_string_with_gpt # Old name
from agents2 import generate_search_string_llm # New name
from agents3 import fetch_papers, save_papers_to_csv, search_elsevier, search_semantic_scholar # agents3.py unchanged by this request
# from agents4 import filter_papers_with_gpt_turbo, generate_response_gpt4_turbo # Old names
from agents4 import filter_papers_llm, generate_response_llm # New names

from flask_cors import CORS
# import requests # Not directly used in this file after refactor
# from datetime import datetime # Already imported

from pathlib import Path

# Explicitly resolve .env path
env_path = Path(__file__).parent / '.env'
print(f"[DEBUG] Loading .env from: {env_path}")
load_dotenv(dotenv_path=env_path)
print(f"[DEBUG] DEEPSEEK_API_KEY at startup: {os.getenv('DEEPSEEK_API_KEY')}")

# ELSEVIER_API_KEY = os.getenv("ELSEVIER_API_KEY") # Renamed for clarity, was 'key'

app = Flask(__name__, static_folder='dist')
CORS(app)

# Default model if not specified by the client
DEFAULT_MODEL = "gpt-3.5-turbo"

@app.route('/api/generate_search_string', methods=['POST'])
def generate_search_string_route():
    data = request.json
    objective = data.get('objective')
    research_questions = data.get('research_questions', [])
    model_name = data.get('model_name', DEFAULT_MODEL)

    if not objective or not research_questions:
        return jsonify({"error": "Objective and research questions are required."}), 400

    # Use the refactored function from agents2.py
    search_string_result = generate_search_string_llm(objective, research_questions, model_name)
    if isinstance(search_string_result, dict) and "error" in search_string_result:
        return jsonify(search_string_result), 500
    return jsonify({"search_string": search_string_result})

@app.route('/api/generate_research_questions_and_purpose', methods=['POST'])
def generate_research_questions_and_purpose_route():
    data = request.json
    objective = data.get('objective')
    num_questions = int(data.get('num_questions', 1))
    model_name = data.get('model_name', DEFAULT_MODEL)

    if not objective:
        return jsonify({"error": "Objective is required"}), 400
    if num_questions < 1:
        return jsonify({"error": "Number of questions must be at least 1"}), 400

    # Use the refactored function from agents.py
    questions_and_purposes = generate_research_questions_and_purpose(objective, num_questions, model_name)
    if "error" in questions_and_purposes: # Check if the result itself is an error dict
         return jsonify(questions_and_purposes), 500 # Or appropriate error code like 502 Bad Gateway if API failed
    return jsonify(questions_and_purposes) # The function already returns {"research_questions": ...} or {"error": ...}


@app.route('/api/filter_papers', methods=['POST'])
def filter_papers_route():
    data = request.json
    search_string = data.get('search_string', '')
    papers = data.get('papers', [])
    model_name = data.get('model_name', DEFAULT_MODEL)
    
    # Use the refactored function from agents4.py
    filtered_papers = filter_papers_llm(search_string, papers, model_name)
    # filter_papers_llm currently doesn't explicitly return error dicts for top level,
    # but good to be prepared if it's enhanced.
    return jsonify({"filtered_papers": filtered_papers})


@app.route('/api/answer_question', methods=['POST'])
def answer_question_route(): # Renamed for clarity
    data = request.json
    questions = data.get('questions')
    papers_info = data.get('papers_info', [])
    model_name = data.get('model_name', DEFAULT_MODEL)
 
    if not questions or not papers_info:
        return jsonify({"error": "Both questions and papers information are required."}), 400
    
    answers = []
    for question in questions:
        # Use the refactored function from agents4.py
        answer_text = generate_response_llm(question, papers_info, model_name)
        # generate_response_llm returns error string or actual answer
        if "An error occurred" in answer_text or "API request failed" in answer_text or "Failed to parse" in answer_text:
            answers.append({"question": question, "answer": answer_text, "error": True}) # Mark error
        else:
            answers.append({"question": question, "answer": answer_text})
    
    return jsonify({"answers": answers})


@app.route('/api/generate-summary-abstract', methods=['POST'])
def generate_summary_abstract_route(): # Renamed for clarity
    try:
        data = request.json
        research_questions = data.get('research_questions', 'No research questions provided.')
        objective = data.get('objective', 'No objective provided.')
        search_string = data.get('search_string', 'No search string provided.')
        model_name = data.get('model_name', DEFAULT_MODEL)

        prompt = (f"Based on the research questions: '{research_questions}', the objective: '{objective}', "
                  f"and the search string: '{search_string}', generate a comprehensive abstract.")

        summary_abstract = generate_abstract_llm(prompt, model_name)
        if isinstance(summary_abstract, dict) and "error" in summary_abstract:
            return jsonify(summary_abstract), 500
        return jsonify({"summary_abstract": summary_abstract})
    except Exception as e:
        print(f"Error in generate_summary_abstract_route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/generate-summary-conclusion", methods=["POST"])
def generate_summary_conclusion_route():
    data = request.json
    papers_info = data.get("papers_info", [])
    model_name = data.get('model_name', DEFAULT_MODEL)
    try:
        summary_conclusion = generate_summary_conclusion_llm(papers_info, model_name)
        if isinstance(summary_conclusion, dict) and "error" in summary_conclusion:
            return jsonify(summary_conclusion), 500
        return jsonify({"summary_conclusion": summary_conclusion})
    except Exception as e:
        print(f"Error in generate_summary_conclusion_route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-introduction-summary', methods=['POST'])
def generate_introduction_summary_route(): # Renamed for clarity
    try:
        data = request.json
        # Corrected: 'papersData' from frontend is all_papers, 'papersFilterData' is filtered_papers
        total_papers_count = len(data.get("total_papers", [])) # Expect 'total_papers' to be the full list
        filtered_papers_count = len(data.get("filtered_papers", []))
        research_questions = data.get("research_questions", [])
        objective = data.get("objective", "")
        search_string = data.get("search_string", "")
        answers = data.get("answers", []) # List of {question: ..., answer: ...}
        model_name = data.get('model_name', DEFAULT_MODEL)

        # Constructing the introduction based on the provided data
        prompt_intro = (f"This document synthesizes findings. Initially, {total_papers_count} papers related to \"{search_string}\" were considered. "
                        f"After filtering, {filtered_papers_count} papers were thoroughly examined. The primary research objective is: {objective}.")
        
        prompt_questions = "\n\nKey Research Questions Addressed:\n" + "\n".join([f"- {q}" for q in research_questions])
        
        # Summarize answers briefly
        answers_summary_parts = []
        for ans_obj in answers:
            if isinstance(ans_obj, dict) and 'question' in ans_obj and 'answer' in ans_obj:
                 # Take first 150 chars of answer for brevity in prompt
                ans_brief = ans_obj['answer'][:150] + "..." if len(ans_obj['answer']) > 150 else ans_obj['answer']
                answers_summary_parts.append(f"- For question '{ans_obj['question']}': {ans_brief}")
        prompt_answers = "\n\nSummary of Key Findings:\n" + "\n".join(answers_summary_parts)
        
        prompt = (f"{prompt_intro}{prompt_questions}{prompt_answers}\n\nBased on this information, "
                  f"generate a coherent introduction and high-level summary of the findings for a research paper section.")

        introduction_summary = generate_introduction_summary_llm(prompt, model_name)
        if isinstance(introduction_summary, dict) and "error" in introduction_summary:
            return jsonify(introduction_summary), 500
        return jsonify({"introduction_summary": introduction_summary})
    except Exception as e:
        print(f"Error in generate_introduction_summary_route: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate-summary-all", methods=["POST"])
def generate_summary_all_route():
    data = request.json
    abstract_summary = data.get("abstract_summary", "No abstract provided.")
    intro_summary = data.get("intro_summary", "No introduction provided.")
    conclusion_summary = data.get("conclusion_summary", "No conclusion provided.")

    try:
        # Ensure templates directory exists
        templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        if not os.path.exists(templates_dir):
            os.makedirs(templates_dir)
            return jsonify({"error": "Templates directory not found and could not be created"}), 500

        # Ensure latex template exists
        template_path = os.path.join(templates_dir, 'latex_template.tex')
        if not os.path.exists(template_path):
            return jsonify({"error": "LaTeX template file not found"}), 500

        latex_content = render_template(
            "latex_template.tex",
            abstract=abstract_summary,
            introduction=intro_summary,
            conclusion=conclusion_summary,
        )

        # Create a temporary file with a proper name
        temp_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.tex', delete=False, encoding='utf-8')
        temp_file_path = temp_file.name
        
        try:
            temp_file.write(latex_content)
            temp_file.close()  # Explicitly close the file before sending
            
            # Send the file
            response = send_file(
                temp_file_path,
                as_attachment=True,
                download_name='paper_summary.tex',
                mimetype='application/x-latex'
            )
            
            # Clean up the temporary file after sending
            @response.call_on_close
            def cleanup():
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    print(f"Error removing temporary file {temp_file_path}: {e}")
            
            return response
            
        except Exception as e:
            # Clean up temp file if something goes wrong
            try:
                os.remove(temp_file_path)
            except:
                pass
            raise e
        
    except Exception as e:
        print(f"Error in generate_summary_all_route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/search_papers', methods=['POST'])
def search_papers_route():
    try:
        data = request.json
        search_string = data.get('search_string')
        start_year = data.get('start_year', datetime.datetime.now().year - 1)
        limit = data.get('limit', 10)
        source = data.get('source', 'scopus')  # Default to scopus for backward compatibility
        
        if not search_string:
            return jsonify({"error": "Search string is required"}), 400
            
        # Call the appropriate search function based on source
        if source.lower() == 'semanticscholar':
            papers = search_semantic_scholar(search_string, start_year, limit)
        else:  # Default to scopus
            papers = search_elsevier(search_string, start_year, start_year, limit)
        
        if isinstance(papers, dict) and "error" in papers:
            return jsonify({"error": papers.get("error", "Failed to fetch papers")}), 500
            
        return jsonify(papers)
        
    except Exception as e:
        print(f"Error in search_papers_route: {e}")
        return jsonify({"error": str(e)}), 500

# --- Static file serving ---
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        # For SPA routing, always serve index.html for unknown paths
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/test-keys', methods=['GET'])
def test_keys():
    import requests
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    result = {
        'deepseek_key_loaded': bool(deepseek_key),
        'openai_key_loaded': bool(openai_key),
        'deepseek_api_status': None,
        'openai_api_status': None,
        'deepseek_message': '',
        'openai_message': ''
    }
    # Test DeepSeek API (example endpoint, adjust as needed)
    if deepseek_key:
        try:
            resp = requests.get(
                'https://api.deepseek.com/v1/models',
                headers={'Authorization': f'Bearer {deepseek_key}'}
            )
            result['deepseek_api_status'] = resp.status_code
            if resp.ok:
                result['deepseek_message'] = 'DeepSeek API key valid.'
            else:
                result['deepseek_message'] = f'DeepSeek API error: {resp.text}'
        except Exception as e:
            result['deepseek_api_status'] = 'error'
            result['deepseek_message'] = str(e)
    # Test OpenAI API (list models)
    if openai_key:
        try:
            resp = requests.get(
                'https://api.openai.com/v1/models',
                headers={'Authorization': f'Bearer {openai_key}'}
            )
            result['openai_api_status'] = resp.status_code
            if resp.ok:
                result['openai_message'] = 'OpenAI API key valid.'
            else:
                result['openai_message'] = f'OpenAI API error: {resp.text}'
        except Exception as e:
            result['openai_api_status'] = 'error'
            result['openai_message'] = str(e)
    return jsonify(result)

if __name__ == '__main__':
    # Ensure the 'templates' folder exists if render_template is used for latex_template.tex
    if not os.path.exists('templates'):
        print("Warning: 'templates' folder not found. LaTeX generation might fail if 'latex_template.tex' is not found by Flask.")
    app.run(debug=True, use_reloader=False)

