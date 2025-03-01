# minimal_app.py
from flask import Flask
import sys

def create_minimal_app():
    """Create a minimal Flask application"""
    print("Creating minimal Flask app...")
    
    # Create Flask app
    app = Flask(__name__)
    
    # Add a simple route
    @app.route('/')
    def index():
        return "Minimal test app running!"
    
    print("Minimal Flask app created successfully")
    return app

if __name__ == "__main__":
    print("Starting minimal app...")
    
    try:
        # Create the app
        app = create_minimal_app()
        
        # Start the server
        print("Starting Flask server...")
        app.run(debug=False, port=5002)  # Use a different port to avoid conflicts
        print("Flask server started")
        
    except Exception as e:
        print(f"Error running minimal app: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)