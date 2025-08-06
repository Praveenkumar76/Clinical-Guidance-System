import sys
from pathlib import Path

# This line adds the project's root directory to the Python path.
# It allows this script to find and import 'main.py' from the parent folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from serverless_wsgi import handle
from main import app  # Imports the 'app' object from your main.py file

def handler(event, context):
    """
    The handler function that Netlify will run.
    """
    return handle(app, event, context)