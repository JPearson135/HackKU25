# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template, session, redirect
from datetime import datetime
from anthropic import Anthropic
import re
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from flask_cors import CORS
import logging
import traceback
import warnings

# Configure logging before any other operations
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

# Suppress specific warnings
warnings.filterwarnings("ignore", message="WARNING! api_key is not default parameter.")
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core.*")

# Modified environment loading - checks Render's environment first
api_key = os.environ.get("ANTHROPIC_API_KEY")  # Check Render's environment first
if not api_key:
    # Fallback to .env file only if not in production
    env_path = Path('.') / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, verbose=True)
        api_key = os.getenv("ANTHROPIC_API_KEY")
    # Log more detailed information about environment variables
    logging.debug(f"Environment variables: {dict(os.environ)}")

if not api_key:
    logging.error("ERROR: ANTHROPIC_API_KEY not found in environment variables or .env file")
    logging.error("Current working directory: %s", os.getcwd())
    logging.error("Files in directory: %s", os.listdir('.'))
    raise ValueError("ANTHROPIC_API_KEY is required")
elif len(api_key.strip()) < 20:
    logging.error("ANTHROPIC_API_KEY appears to be malformed. Please check the value.")
else:
    logging.info("ANTHROPIC_API_KEY loaded successfully")

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['JSON_AS_ASCII'] = False
CORS(app)

# Domain configuration - modified for Render compatibility
PRODUCTION_DOMAIN = 'feelgoodbot.us'
ALLOWED_HOSTS = ['*']  # Allow all hosts for deployment

# Security configuration
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key'))

# UPDATED MODEL NAME: Using the full version with date
CLAUDE_MODEL = "claude-3-haiku-20240307"

# Initialize LLM with correct parameters and updated model name
llm = ChatAnthropic(
    model_name=CLAUDE_MODEL,  # Using the updated model name
    temperature=0.7,
    max_tokens=1024,
    api_key=api_key
)

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=api_key)

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "don't want to live",
    "hurt myself", "self-harm", "die", "death"
]

CRISIS_RESOURCES = """
If you're experiencing a crisis or having thoughts of harming yourself:
- National Suicide Prevention Lifeline: 988 or 1-800-273-8255
- Crisis Text Line: Text HOME to 741741
- Emergency Services: Call 911 or go to your nearest emergency room
- International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/
"""

THERAPEUTIC_PROMPT = """
You are MindfulMate, a compassionate AI assistant providing:
- Mental health support (anxiety, depression, stress)
- Emotional guidance (relationships, grief, self-esteem)
- Life advice (decision-making, motivation, personal growth)

Guidelines:
1. Always respond with empathy and validation first
2. Ask thoughtful questions to understand the situation
3. Offer evidence-based coping strategies when appropriate
4. Structure your response in these sections when applicable:
   - Understanding (validating their feelings)
   - Perspective (offering a thoughtful view)
   - Practical Tips (2-3 specific actionable suggestions)
   - Question (one thoughtful question to promote reflection)
5. Maintain professional boundaries and never claim to replace therapy
6. For crisis situations:
   - Provide immediate validation
   - Offer crisis resources
   - Encourage contacting professionals

Important disclaimers to remember:
- You are not a licensed therapist or healthcare provider
- Your suggestions are not professional medical advice
- Users should consult qualified professionals for serious concerns
"""

conversation_histories = {}

@app.before_request
def enforce_https_and_domain():
    """Modified for Render compatibility"""
    # Skip these checks for health checks and static files
    if request.path.startswith('/static/') or request.path == '/health':
        return
    
    # Redirect to HTTPS if not secure
    if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
        if 'http://' in request.url:
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/disclaimer")
def show_disclaimer():
    return render_template("disclaimer.html")

@app.route("/resources")
def show_resources():
    return render_template("resources.html")

@app.route("/test")
def test():
    return jsonify({"status": "success", "message": "Test route is working!"})

@app.route("/test-llm")
def test_llm():
    try:
        test = llm.invoke([HumanMessage(content="Hello")])
        return jsonify({
            "success": True,
            "response": str(test.content),
            "model": CLAUDE_MODEL,
            "api_status": "working"
        })
    except Exception as e:
        logging.error("Detailed LLM Test Error: %s", str(e))
        return jsonify({
            "success": False,
            "error": str(e),
            "model": CLAUDE_MODEL,
            "api_status": "failed"
        }), 500

@app.route("/test-llm-detailed")
def test_llm_detailed():
    try:
        # Use the direct Anthropic client for testing with updated model name
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        # Log the complete response for debugging
        logging.debug(f"Complete API response: {response}")
        
        return jsonify({
            "success": True,
            "response": response.content[0].text if hasattr(response, 'content') and response.content else "No content returned",
            "model": CLAUDE_MODEL,
            "api_status": "working",
            "api_key_length": len(api_key) if api_key else 0,
            "api_key_valid": bool(api_key and len(api_key.strip()) >= 20),
            "environment": os.environ.get("FLASK_ENV", "production"),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Detailed LLM Test Error: {str(e)}")
        traceback_str = traceback.format_exc()
        logging.error(f"Traceback: {traceback_str}")
        return jsonify({
            "success": False,
            "error": str(e),
            "model": CLAUDE_MODEL,
            "api_status": "failed",
            "api_key_length": len(api_key) if api_key else 0,
            "api_key_valid": bool(api_key and len(api_key.strip()) >= 20),
            "environment": os.environ.get("FLASK_ENV", "production"),
            "timestamp": datetime.now().isoformat()
        }), 500

def check_for_crisis(message):
    message_lower = message.lower()
    for keyword in CRISIS_KEYWORDS:
        if keyword in message_lower:
            return True
    return False

@app.route("/chat", methods=["POST"])
def chat():
    try:
        logging.debug("Received a request to /chat endpoint")
        data = request.get_json()
        if not data:
            logging.error("No data received in the request")
            return jsonify({"error": "No data received"}), 400
            
        user_message = data.get('message', '').strip()
        user_id = data.get('user_id', 'anonymous')
        
        logging.debug(f"User ID: {user_id}, User Message: {user_message}")
        
        if not user_message:
            logging.error("Empty message received")
            return jsonify({"error": "Empty message"}), 400

        if user_id not in conversation_histories:
            logging.debug("Initializing conversation history for new user")
            conversation_histories[user_id] = [
                SystemMessage(content=THERAPEUTIC_PROMPT)
            ]
        
        conversation_histories[user_id].append(HumanMessage(content=user_message))
        
        is_crisis = check_for_crisis(user_message)
        logging.debug(f"Crisis detected: {is_crisis}")
        
        if len(conversation_histories[user_id]) > 11:
            logging.debug("Trimming conversation history to last 10 messages")
            conversation_histories[user_id] = [
                conversation_histories[user_id][0]
            ] + conversation_histories[user_id][-10:]
        
        try:
            logging.debug("Sending conversation history to LLM")
            response = llm.invoke(conversation_histories[user_id])
            
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            logging.debug(f"LLM Response: {response_text[:100]}...")
            
            conversation_histories[user_id].append(AIMessage(content=response_text))
            
            if is_crisis:
                response_text += "\n\n" + CRISIS_RESOURCES
            
            return jsonify({
                "response": response_text,
                "status": "success",
                "is_crisis": is_crisis
            })
            
        except Exception as e:
            logging.error(f"LLM API Error: {str(e)}")
            error_message = str(e).lower()
            if "api key" in error_message or "auth" in error_message or "401" in error_message:
                return jsonify({
                    "response": "There's an issue with the AI service authentication. Please contact support.",
                    "status": "error",
                    "error_details": "API authentication error"
                }), 500
            else:
                raise
                
    except Exception as e:
        logging.error(f"Error in /chat endpoint: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            "response": "I encountered an error processing your request. Please try again.",
            "status": "error",
            "error_details": str(e)
        }), 500

@app.route("/feedback", methods=["POST"])
def handle_feedback():
    try:
        data = request.get_json()
        logging.info(f"Received feedback: {data}")
        return jsonify({"status": "success", "message": "Feedback received"})
    except Exception as e:
        logging.error(f"Error processing feedback: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    try:
        print("Testing API connection...")
        test = llm.invoke([HumanMessage(content="Hello")])
        print(f"API Test Success: {test.content[:50]}...")
    except Exception as e:
        print(f"API Test Failed: {str(e)}")
        
    app.run(host='0.0.0.0', port=5000, debug=False)