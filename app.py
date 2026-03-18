from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
import json
import os
import re

app = Flask(__name__, static_folder='.')
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are CropSight, an expert agricultural AI that analyzes aerial drone/satellite farm images.

Analyze the provided aerial farm image and return ONLY a valid JSON response with this exact structure:

{
  "overall_health": "Good" or "Average" or "Bad",
  "confidence_score": <number 0-100>,
  "summary": "<2-3 sentence plain English summary for a farmer>",
  "zones": [
    {
      "zone_id": "Zone A",
      "health": "Good" or "Average" or "Bad",
      "coverage_percent": <estimated % of image>,
      "color_description": "<what you see: lush green, yellowing, brown patches, etc>"
    }
  ],
  "detected_issues": [
    {
      "issue": "<issue name e.g. Nitrogen Deficiency>",
      "severity": "Low" or "Medium" or "High",
      "description": "<1 sentence explanation>"
    }
  ],
  "recommended_actions": [
    {
      "priority": "Immediate" or "This Week" or "Monitor",
      "action": "<specific actionable step>",
      "reason": "<why this action is needed>"
    }
  ]
}

Rules:
- Be specific and accurate to what you see in the image
- If the image is not a farm/crop image, still analyze the greenery present
- Zones should reflect visually distinct regions you can see (2-4 zones typically)
- Recommended actions should be practical for a smallholder farmer
- Always return valid JSON only, no markdown, no extra text
"""

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image provided'}), 400

        image_data = data['image']
        mime_type = 'image/jpeg'
        if ',' in image_data:
            header, image_data = image_data.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]

        model = genai.GenerativeModel('gemini-3-flash-preview')
        image_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": image_data
            }
        }

        response = model.generate_content([SYSTEM_PROMPT, image_part])
        raw = response.text.strip()

        # Strip markdown fences if present
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        result = json.loads(raw)
        return jsonify({'success': True, 'data': result})

    except json.JSONDecodeError as e:
        return jsonify({'error': f'AI response parse error: {str(e)}', 'raw': response.text if 'response' in locals() else ''}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🌱 CropSight backend running on http://localhost:5000")
    app.run(debug=True, port=5000)
