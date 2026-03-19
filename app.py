from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
import json
import os
import re
import base64
import io
from PIL import Image

app = Flask(__name__, static_folder='.')
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """Analyze this farm zone image. Return ONLY a valid JSON with two fields:
{
  "score": <number 1-10 where 1=worst, 10=best>,
  "summary": "<1 brief sentence describing what you see>"
}
"""

HISTORY_FILE = 'analysis_history.json'

def load_history():
    """Load analysis history from JSON file"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    """Save analysis history to JSON file"""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving history: {e}")
        return False

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/load-history', methods=['GET'])
def get_history():
    """Load analysis history from file"""
    history = load_history()
    return jsonify({'success': True, 'data': history})

@app.route('/save-history', methods=['POST'])
def add_to_history():
    """Save analysis history item"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        history = load_history()
        # Add new item to the beginning (newest first)
        history.insert(0, data)
        
        # Keep only last 100 items to avoid file getting too large
        history = history[:100]
        
        if save_history(history):
            return jsonify({'success': True, 'data': history})
        else:
            return jsonify({'error': 'Failed to save history'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete-history/<int:index>', methods=['DELETE'])
def delete_history_item(index):
    """Delete a history item by index"""
    try:
        history = load_history()
        if 0 <= index < len(history):
            history.pop(index)
            if save_history(history):
                return jsonify({'success': True, 'data': history})
        return jsonify({'error': 'Invalid index'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear-history', methods=['DELETE'])
def clear_all_history():
    """Clear all history"""
    try:
        if save_history([]):
            return jsonify({'success': True, 'data': []})
        return jsonify({'error': 'Failed to clear history'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image provided'}), 400

        image_data = data['image']
        selected_zones = data.get('selected_zones', None)
        mime_type = 'image/jpeg'
        if ',' in image_data:
            header, image_data = image_data.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]

        # Resize image to save tokens
        img_bytes = base64.b64decode(image_data)
        img = Image.open(io.BytesIO(img_bytes))
        
        # Calculate new size maintaining aspect ratio (max 128x128 for lowest possible quota usage)
        max_size = (128, 128)
        resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
        img.thumbnail(max_size, resample_filter)
        
        # Convert back to base64
        buffered = io.BytesIO()
        img_format = 'JPEG' if mime_type == 'image/jpeg' else 'PNG'
        img.save(buffered, format=img_format, quality=85)
        resized_image_data = base64.b64encode(buffered.getvalue()).decode('utf-8')

        model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        image_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": resized_image_data
            }
        }
        
        prompt_to_use = SYSTEM_PROMPT

        response = model.generate_content([prompt_to_use, image_part])
        raw = response.text.strip()

        # Strip markdown fences if present
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        ai_result = json.loads(raw)
        
        # Fallback values if AI didn't return them correctly
        score = ai_result.get('score', 5)
        ai_summary = ai_result.get('summary', 'Analysis complete.')
        
        # --- TREND ANALYSIS LOGIC ---
        trend_text = ""
        if selected_zones and len(selected_zones) > 0:
            row = selected_zones[0].get('row', 0)
            col = selected_zones[0].get('col', 0)
            
            history = load_history()
            # Find the most recent previous analysis for this zone
            previous_score = None
            for item in history:
                if item.get('row') == row and item.get('col') == col:
                    previous_score = item.get('score')
                    break
            
            if previous_score is not None:
                diff = score - previous_score
                
                # Personalized username logic
                username = data.get('username')
                user_prefix = f"{username.capitalize()}, the " if username else "The "
                
                if diff > 0:
                    trend_text = f" 📈 Trend: {user_prefix}health improved (+{diff}) since previous analysis."
                elif diff < 0:
                    trend_text = f" 📉 Trend: {user_prefix}health declined (-{abs(diff)}) since previous analysis."
                else:
                    trend_text = f" ➖ Trend: {user_prefix}health remained stable since previous analysis."
        
        # Append trend to summary
        ai_summary += trend_text
        
        # --- LOCAL GENERATION LOGIC ---
        
        # Determine overall health
        if score >= 7:
            overall_health = "Good"
            confidence = 85 + score
            issues = []
            actions = [
                {
                    "priority": "Monitor",
                    "action": "Maintain current practices",
                    "reason": "Crop appears healthy with no immediate intervention needed."
                }
            ]
        elif score >= 4:
            overall_health = "Average"
            confidence = 70 + score
            issues = [
                {
                    "issue": "Suboptimal Growth",
                    "severity": "Medium",
                    "description": "Some areas show signs of stress or uneven development."
                }
            ]
            actions = [
                {
                    "priority": "This Week",
                    "action": "Check soil moisture and nutrient levels",
                    "reason": "Early intervention can prevent further degradation."
                }
            ]
        else:
            overall_health = "Bad"
            confidence = 90 - score
            issues = [
                {
                    "issue": "Severe Crop Stress",
                    "severity": "High",
                    "description": "Visible signs of disease, severe nutrient deficiency, or drought."
                }
            ]
            actions = [
                {
                    "priority": "Immediate",
                    "action": "Conduct immediate physical inspection",
                    "reason": "Critical issues detected requiring immediate mitigation to prevent loss."
                }
            ]

        # Construct the final JSON payload expected by the frontend
        final_result = {
            "overall_health": overall_health,
            "confidence_score": confidence,
            "summary": ai_summary,
            "zone_grid": [],
            "detected_issues": issues,
            "recommended_actions": actions
        }

        # If specific zones were selected, put the result in those zones
        if selected_zones and len(selected_zones) > 0:
            for zone in selected_zones:
                row = zone.get('row', 0)
                col = zone.get('col', 0)
                final_result["zone_grid"].append({
                    "row": row,
                    "col": col,
                    "health": overall_health,
                    "score_1_10": score,
                    "description": ai_summary
                })

        return jsonify({'success': True, 'data': final_result})

    except json.JSONDecodeError as e:
        return jsonify({'error': f'AI response parse error: {str(e)}', 'raw': response.text if 'response' in locals() else ''}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🌱 Krishikaran backend running on http://localhost:5000")
    print(f"📊 Analysis history will be saved to: {HISTORY_FILE}")
    app.run(debug=True, port=5000)
