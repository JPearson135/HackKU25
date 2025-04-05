from flask import Flask, request, jsonify
import random
from datetime import datetime
import re
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import Tool
from tools import search_tool, wiki_tool, save_tool

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_default_secret_key_here')

# Initialize the research agent
class ResearchResponse(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]

research_parser = PydanticOutputParser(pydantic_object=ResearchResponse)

research_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a research assistant that will help generate a research paper. Answer the user query and use necessary tools. 
            Wrap the output in this format and provide no other text\n{format_instructions}
            """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=research_parser.get_format_instructions())

tools = [search_tool, wiki_tool, save_tool]
llm = ChatAnthropic(model="claude-3-sonnet-20240229")  # Updated model name

research_agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=research_prompt
)

research_executor = AgentExecutor(
    agent=research_agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    return_intermediate_steps=True
)

# Therapeutic responses
THERAPEUTIC_RESPONSES = {
    "greeting": [
        "Hello, I'm here to help with your research or just listen. How can I assist you today?",
        "Welcome. I can help with research or just chat. What would you like to do?",
        "Hi there. I'm here to help with research or provide support. What's on your mind?"
    ],
    "research": [
        "I'll research that for you. Just a moment...",
        "Let me look into that topic for you...",
        "I'll gather some information about that..."
    ],
    "fallback": [
        "I'm not sure I understand. Would you like help with research or just to talk?",
        "Could you clarify? I can help with research or just listen.",
        "I want to make sure I help appropriately. Are you looking for information or support?"
    ]
}

user_sessions = {}

def detect_intent(message):
    """Detect if the user wants research help or therapeutic conversation"""
    message_lower = message.lower()
    
    research_keywords = [
        "research", "find information", "look up", "search for",
        "what is", "who is", "when was", "how does", "tell me about"
    ]
    
    if any(keyword in message_lower for keyword in research_keywords):
        return "research"
    return "chat"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message')
    user_id = data.get('user_id', 'default_user')

    if not user_message:
        return jsonify({"error": "No message received"}), 400
    
    try:
        intent = detect_intent(user_message)
        
        if intent == "research":
            response = random.choice(THERAPEUTIC_RESPONSES["research"])
            
            try:
                raw_response = research_executor.invoke({"input": user_message})
                
                if isinstance(raw_response['output'], dict):
                    structured_response = raw_response['output']
                    response = f"Here's what I found:\n\n{structured_response.get('summary', 'No summary available')}"
                    if structured_response.get('sources'):
                        response += f"\n\nSources: {', '.join(structured_response['sources'])}"
                else:
                    response = raw_response['output']
                    
            except Exception as e:
                print("Error in research execution:", e)
                response = "I encountered an error while researching that topic. Could you try rephrasing your question?"
            
            return jsonify({
                "response": response,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            # Therapeutic chat response
            if user_id not in user_sessions:
                response = random.choice(THERAPEUTIC_RESPONSES["greeting"])
                user_sessions[user_id] = {"first_seen": datetime.now()}
            else:
                response = random.choice([
                    "I'm here to listen. How does that make you feel?",
                    "That's interesting. Tell me more about that.",
                    "I understand. Would you like to explore this further?"
                ])
            
            return jsonify({
                "response": response,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({
            "response": "I'm having trouble processing that. Could you try again?",
            "user_id": user_id,
            "error": "internal_server_error"
        }), 500

@app.route('/session/<user_id>', methods=['GET'])
def get_session(user_id):
    if user_id in user_sessions:
        return jsonify({
            "status": "success",
            "session": user_sessions[user_id]
        })
    return jsonify({"status": "session_not_found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
