import sys
import os
from dotenv import load_dotenv
from gui.MainWindow import main

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Verify required environment variables
    required_vars = [
        "OPENROUTER_API_KEY",
        "STABILITY_API_KEY",
        "ELEVENLABS_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        sys.exit(1)
    
    # Start the application
    main()
