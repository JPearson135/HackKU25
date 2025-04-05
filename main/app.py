from flask import Flask, request, jsonify, session
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this for production

# Therapeutic responses organized by category
THERAPEUTIC_RESPONSES = {
    "greeting": [
        "Hello, I'm here to listen. How are you feeling today?",
        "Welcome. I'm ready to support you. What's on your mind?",
        "Hi there. I notice you've come to talk. How can I help?"
    ],
    "exploration": [
        "Tell me more about that.",
        "How does that make you feel?",
        "What do you think is at the root of this feeling?",
        "Can you describe what that experience was like for you?"
    ],
    "validation": [
        "That sounds really difficult. I can understand why you'd feel that way.",
        "Your feelings are completely valid.",
        "It makes sense you'd feel that way given what you've been through."
    ],
    "reflection": [
        "It seems like you're saying... [rephrase their statement]",
        "I hear you saying that... [summarize their words]",
        "Would it be accurate to say you feel... [identify emotion]?"
    ],
    "encouragement": [
        "You're showing a lot of courage by talking about this.",
        "I appreciate you sharing that with me.",
        "This is important work you're doing for yourself."
    ],
    "closing": [
        "Our time is ending for now. How are you feeling about what we discussed?",
        "Before we finish, is there anything else you'd like to share?",
        "I'd like to leave you with this thought: You're stronger than you think."
    ]
}

# Track conversation history and user state
user_sessions = {}

def ai_therapist(message, user_id):
    # Initialize session if new user
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'start_time': datetime.now(),
            'message_count': 0,
            'conversation_history': []
        }
    
    session = user_sessions[user_id]
    session['message_count'] += 1
    session['conversation_history'].append(('user', message))
    
    # Determine response strategy based on conversation
    if session['message_count'] == 1:
        response = random.choice(THERAPEUTIC_RESPONSES["greeting"])
    elif "goodbye" in message.lower() or "bye" in message.lower():
        response = random.choice(THERAPEUTIC_RESPONSES["closing"])
    else:
        # Analyze message for emotional content (simple version)
        emotional_words = ['sad', 'happy', 'angry', 'anxious', 'depressed', 'excited']
        if any(word in message.lower() for word in emotional_words):
            response = random.choice(THERAPEUTIC_RESPONSES["validation"] + THERAPEUTIC_RESPONSES["exploration"])
        else:
            response = random.choice(THERAPEUTIC_RESPONSES["exploration"] + THERAPEUTIC_RESPONSES["reflection"])
    
    session['conversation_history'].append(('therapist', response))
    return response

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message')
    user_id = data.get('user_id', 'default_user')  # In production, use actual user auth

    if not user_message:
        return jsonify({"error": "No message received"}), 400
    
    response = ai_therapist(user_message, user_id)
    return jsonify({
        "response": response,
        "user_id": user_id  # Return the user_id for the frontend to maintain
    })

if __name__ == '__main__':
    app.run(debug=True)