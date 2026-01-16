import threading
import uvicorn
from main import RoverController

def start_api():
    uvicorn.run(
        "control_server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    rover = RoverController()
    rover.run()
