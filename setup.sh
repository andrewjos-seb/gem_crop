#!/bin/bash

echo ""
echo "🌾 CropSight — Setup Script"
echo "================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Install it with: sudo apt install python3"
    exit 1
fi

echo "✅ Python3 found: $(python3 --version)"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt --break-system-packages

echo ""
echo "================================"
echo "✅ Setup complete!"
echo ""
echo "👉 Next step: Set your Gemini API key"
echo "   export GEMINI_API_KEY='your_key_here'"
echo ""
echo "👉 Then run the server:"
echo "   python3 app.py"
echo ""
echo "🌐 Open: http://localhost:5000"
echo "================================"
