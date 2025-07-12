#!/bin/bash

# Jira LangChain Setup Script
echo "🚀 Setting up Jira LangChain Automation Tool..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚙️  No .env file found. Would you like to create one now? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "🔐 Running interactive setup..."
        python main.py setup
    else
        echo "📝 Please copy .env.example to .env and configure your settings:"
        echo "   cp .env.example .env"
        echo "   # Edit .env with your Jira and LLM API credentials"
    fi
fi

echo ""
echo "✅ Setup complete! You can now use the tool:"
echo ""
echo "   # Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "   # Run the tool:"
echo "   python main.py -i sample_tickets.txt --dry-run"
echo ""
echo "   # Get help:"
echo "   python main.py --help"
echo ""
echo "   # Test with the sample file:"
echo "   python main.py -i sample_tickets.txt --dry-run --verbose"
echo ""
echo "📖 Check the README.md for more detailed usage instructions."
