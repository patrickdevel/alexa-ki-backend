from flask import Flask, request, jsonify
from groq import Groq
import os

app = Flask(__name__)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = (
    "Du bist ein absolut präzises KI-Gehirn für einen Alexa Skill. Antworte kurz "
    "in maximal 2-3 Sätzen. Wenn du dir bei einem Fakt oder einer Zahl nicht zu "
    "100 % sicher bist, erfinde NIEMALS etwas, sondern sage stattdessen knallhart: "
    "'Das weiß ich leider nicht.'"
)

@app.route("/api/alexa", methods=["POST"])
def alexa_skill():
    data = request.get_json()
    request_type = data.get("request", {}).get("type")
    
    # Verlauf aus den Session-Attributen holen (falls vorhanden)
    session = data.get("session", {})
    attributes = session.get("attributes", {})
    chat_history = attributes.get("chat_history", [])

    # 1. Wenn der Skill gestartet wird
    if request_type == "LaunchRequest":
        return respond("(By Patrick Roth) Hi! Ich bin dein KI-Assistent. Was gibt's?", chat_history)

    # 2. Wenn ein Sprachbefehl reinkommt
    elif request_type == "IntentRequest":
        intent_name = data["request"]["intent"]["name"]
        
        if intent_name == "AskAiIntent":
            try:
                user_text = data["request"]["intent"]["slots"]["meinText"]["value"]
                
                # Nutzersatz zum Verlauf hinzufügen
                chat_history.append({"role": "user", "content": user_text})
                
                # Payload für Groq zusammenbauen (System Prompt + Verlauf)
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history
                
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages
                )
                ai_response = completion.choices[0].message.content
                
                # KI-Antwort zum Verlauf hinzufügen
                chat_history.append({"role": "assistant", "content": ai_response})
                
                return respond(ai_response, chat_history)
                
            except Exception as e:
                return respond("Fehler beim Verarbeiten der KI-Antwort.", chat_history)

    return respond("Alles klar, bis bald!", chat_history, end_session=True)

def respond(text, chat_history, end_session=False):
    """Hilfsfunktion, die den Verlauf in sessionAttributes zurückgibt"""
    return jsonify({
        "version": "1.0",
        "sessionAttributes": {
            "chat_history": chat_history
        },
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": text
            },
            "shouldEndSession": end_session
        }
    })

