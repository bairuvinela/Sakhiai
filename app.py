import os
import uuid
import whisper
import requests
from flask import Flask, render_template, request, send_file
from groq import Groq
from dotenv import load_dotenv

# Load env variables
load_dotenv()

app = Flask(__name__)

# API Keys (kept as you wrote)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# Load Whisper model
model = whisper.load_model("base")

# ========== SPEECH TO TEXT ==========
def speech_to_text(audio_path):
    try:
        # 🔥 FIX: better decoding
        result = model.transcribe(audio_path, fp16=False, language='en')
        text = result["text"].strip()

        if text == "":
            return "I couldn't hear anything"

        print("User said:", text)
        return text

    except Exception as e:
        print("Whisper Error:", e)
        return "I couldn't understand that"

# ========== AI RESPONSE ==========
def generate_response(user_text):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a compassionate mental health assistant. "
                        "Respond in English. Be empathetic, supportive, and natural like a human."
                    )
                },
                {"role": "user", "content": user_text}
            ]
        )

        reply = response.choices[0].message.content
        print("AI Response:", reply)
        return reply

    except Exception as e:
        print("Groq Error:", e)
        return "I'm here for you. Can you tell me more about how you're feeling?"

# ========== TEXT TO SPEECH ==========
def text_to_speech(text, filename):
    url = "https://api.murf.ai/v1/speech/generate"

    payload = {
        "text": text,
        "voiceId": "en-US-natalie",
        "format": "mp3"
    }

    headers = {
        "api-key": "ap2_ae463a11-2053-471e-bb06-97a690d0e5f5",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    print("Murf Status:", response.status_code)

    if response.status_code != 200:
        print("Murf Error:", response.text)
        raise Exception("Murf API failed")

    # 🔥 FIX STARTS HERE
    data = response.json()
    audio_url = data.get("audioFile")

    if not audio_url:
        raise Exception("No audio URL from Murf")

    # Download actual MP3
    audio_data = requests.get(audio_url)

    with open(filename, "wb") as f:
        f.write(audio_data.content)

    print("Audio file saved:", filename)

    return filename
# ========== ROUTES ==========
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    try:
        audio = request.files["audio"]

        # Save input audio
        input_path = f"outputs/{uuid.uuid4()}.webm"
        audio.save(input_path)
        print("Audio saved:", input_path)

        # Speech → Text
        text = speech_to_text(input_path)

        # AI Response
        response_text = generate_response(text)

        # Text → Speech
        output_path = f"outputs/{uuid.uuid4()}.mp3"
        text_to_speech(response_text, output_path)

        print("Sending audio file:", output_path)  # 🔥 debug

        # 🔥 FIX: correct mimetype
        return send_file(
            output_path,
            mimetype="audio/mpeg",
            as_attachment=False
        )

    except Exception as e:
        print("SERVER ERROR:", e)
        return "Error occurred", 500

# ========== RUN ==========
if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)
    app.run(debug=True)