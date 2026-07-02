from flask import Flask, request, jsonify
import google.generativeai as genai
import os

app = Flask(__name__)

# Google Gemini konfigurieren
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = (
    "Du bist ein absolut präzises KI-Gehirn für einen Alexa Skill. Antworte kurz "
    "in maximal 2-3 Sätzen. Wenn du dir bei einem Fakt oder einer Zahl nicht zu "
    "100 % sicher bist, erfinde NIEMALS etwas, sondern sage stattdessen knallhart: "
    "'Das weiß ich nicht.'"
)

@app.route("/api/alexa", methods=["POST"])
def alexa_skill():
    data = request.get_json()
    request_type = data.get("request", {}).get("type")
    
    # Verlauf aus den Session-Attributen holen
    session = data.get("session", {})
    attributes = session.get("attributes", {})
    chat_history = attributes.get("chat_history", [])

    if request_type == "LaunchRequest":
        return respond("Hi! Ich bin dein KI-Assistent. Was gibt's?", chat_history)

    elif request_type == "IntentRequest":
        intent_name = data["request"]["intent"]["name"]
        
        if intent_name == "AskAiIntent":
            try:
                user_text = data["request"]["intent"]["slots"]["meinText"]["value"]
                
                # Nutzersatz zum Verlauf hinzufügen
                chat_history.append({"role": "user", "content": user_text})
                
                # Gemini-Modell initialisieren
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=SYSTEM_PROMPT
                )
                
                # Verlauf für Gemini übersetzen (Google nutzt 'user' und 'model')
                gemini_history = []
                for msg in chat_history:
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append({"role": role, "parts": [msg["content"]]})
                
                # Chat starten und Antwort generieren
                chat = model.start_chat(history=gemini_history[:-1])
                response = chat.send_message(user_text)
                ai_response = response.text
                
                # KI-Antwort zum Verlauf hinzufügen
                chat_history.append({"role": "assistant", "content": ai_response})
                
                return respond(ai_response, chat_history)
                
            except Exception as e:
                return respond("Fehler beim Verarbeiten der KI-Antwort.", chat_history)

    return respond("Alles klar, bis bald!", chat_history, end_session=True)

def respond(text, chat_history, end_session=False):
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
