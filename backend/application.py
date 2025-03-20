# application.py
from app import create_app

# Create the Flask application
application = create_app()

# For local execution
if __name__ == "__main__":
    application.run(host='0.0.0.0', port=5000)