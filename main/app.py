from flask import Flask, request, jsonify, render_template, session
from datetime import datetime
import re
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from flask_cors import CORS
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    logging.error("ANTHROPIC_API_KEY is missing. Please check your .env file.")
elif len(api_key.strip()) < 20:
    logging.error("ANTHROPIC_API_KEY appears to be malformed. Please check the value.")
else:
    logging.info("ANTHROPIC_API_KEY loaded successfully")

app = Flask(__name__)
# Updated CORS configuration to allow all origins for all endpoints
CORS(app)  # This allows all origins for all routes

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_secret_key')

llm = ChatAnthropic(
    model="claude-3-7-sonnet-20250219",
    temperature=0.7,
    max_tokens=1024,
    anthropic_api_key=api_key
)

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

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/test-llm")
def test_llm():
    try:
        test = llm.invoke([HumanMessage(content="Hello")])
        return jsonify({
            "success": True,
            "response": str(test.content),
            "model": llm.model
        })
    except Exception as e:
        logging.error("LLM Test Error: %s", str(e))
        return jsonify({
            "success": False,
            "error": str(e),
            "model": llm.model if hasattr(llm, 'model') else 'unknown'
        }), 500
        
@app.route("/test-llm-detailed")
def test_llm_detailed():
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return jsonify({
                "success": False,
                "error": "API key not found in environment"
            }), 500
            
        key_preview = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "invalid_format"
        
        test = llm.invoke([HumanMessage(content="Hello")])
        return jsonify({
            "success": True,
            "response": str(test.content),
            "model": llm.model,
            "key_format": key_preview
        })
    except Exception as e:
        logging.error("LLM Test Error: %s", str(e))
        return jsonify({
            "success": False,
            "error": str(e),
            "model": llm.model if hasattr(llm, 'model') else 'unknown',
            "key_format": key_preview if 'key_preview' in locals() else "unknown"
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
        
    app.run(host='0.0.0.0', port=5000, debug=True)