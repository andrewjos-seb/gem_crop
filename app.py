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

SYSTEM_PROMPT = """You are Krishikaran, an expert agricultural AI that analyzes aerial drone/satellite farm images.

You MUST divide the image into a 5x5 grid (25 zones total) and analyze each zone individually.

Analyze the provided aerial farm image and return ONLY a valid JSON response with this exact structure:

{
  "overall_health": "Good" or "Average" or "Bad",
  "confidence_score": <number 0-100>,
  "summary": "<2-3 sentence plain English summary for a farmer>",
  "zone_grid": [
    {
      "row": 0,
      "col": 0,
      "health": "Good" or "Average" or "Bad",
      "score": <number 0-100>,
      "score_1_10": <number 1-10 where 1-3=Bad, 4-6=Average, 7-10=Good>,
      "description": "<brief description of this zone>"
    }
  ],
  "manual_zones": [
    {
      "zone_id": "Zone-1",
      "health": "Good" or "Average" or "Bad",
      "score_1_10": <number 1-10>,
      "color_description": "<what you see in this zone>",
      "analysis": "<detailed analysis of this zone>"
    }
  ],
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
- CRITICAL: Analyze all 25 grid zones (5 rows × 5 columns), each with row (0-4) and col (0-4)
- Each grid zone should have:
  * health status (Good/Average/Bad)
  * score_0_100 (0-100 scale)
  * score_1_10 (1-10 scale where 1=worst/bad, 10=best/good; 1-3=Bad, 4-6=Average, 7-10=Good)
- If manual zones are provided by the user, include a "manual_zones" section analyzing only those zones with detailed analysis
- Be specific and accurate to what you see in each zone
- If the image is not a farm/crop image, still analyze the greenery present
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
        manual_zones = data.get('manual_zones', None)
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
        
        # Build prompt with manual zones info if provided
        prompt_to_use = SYSTEM_PROMPT
        if manual_zones and len(manual_zones) > 0:
            zones_info = f"\n\nUSER-DEFINED ZONES TO ANALYZE:\nThe user has manually defined {len(manual_zones)} regions of interest on this image. Analyze each of these regions in detail:\n\n"
            for i, z in enumerate(manual_zones, 1):
                zones_info += f"- {z.get('id', f'Region {i}')}: Position X={z.get('x', 0)}px, Y={z.get('y', 0)}px, Width={z.get('width', 0)}px, Height={z.get('height', 0)}px\n"
            zones_info += "\nProvide detailed analysis with score_1_10 (1-10 scale) for EACH user-defined zone in the 'manual_zones' section of your JSON response."
            prompt_to_use = SYSTEM_PROMPT + zones_info

        response = model.generate_content([prompt_to_use, image_part])
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
    print("🌱 Krishikaran backend running on http://localhost:5000")
    app.run(debug=True, port=5000)
