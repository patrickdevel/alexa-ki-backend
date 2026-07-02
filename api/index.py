from flask import Flask, request, jsonify
from groq import Groq
import os

app = Flask(__name__)

# Initialisiert den Groq-Client (API-Key ziehen wir aus den Umgebungsvariablen)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

@app.route("/api/alexa", methods=["POST"])
def alexa_skill():
    data = request.get_json()
    request_type = data.get("request", {}).get("type")

    # 1. Wenn der Skill gestartet wird ("Alexa, öffne Super AI")
    if request_type == "LaunchRequest":
        return respond("Hi! Ich bin dein KI-Assistent. Was gibt's?")

    # 2. Wenn ein Sprachbefehl reinkommt
    elif request_type == "IntentRequest":
        intent_name = data["request"]["intent"]["name"]
        
        if intent_name == "AskAiIntent":
            try:
                # Extrahiere den gesprochenen Text aus dem Slot
                user_text = data["request"]["intent"]["slots"]["meinText"]["value"]
                
                # Schicke den Text an Groq (LLM)
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "Du bist ein schlaues, direktes KI-Gehirn für einen Alexa Skill. Antworte immer kurz, knackig und direkt in maximal 2-3 Sätzen, damit es flüssig vorgelesen werden kann."},
                        {"role": "user", "content": user_text}
                    ]
                )
                ai_response = completion.choices[0].message.content
                return respond(ai_response)
                
            except Exception as e:
                return respond("Fehler beim Verarbeiten der KI-Antwort.")

    # Standard-Antwort für Abbruch/Stopp
    return respond("Alles klar, bis bald!", end_session=True)

def respond(text, end_session=False):
    """Hilfsfunktion für das korrekte Alexa JSON-Format"""
    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": text
            },
            "shouldEndSession": end_session
        }
    })
