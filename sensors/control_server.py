from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import config
import movement_test   # 👈 import test

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_methods=["*"],
    allow_headers=["*"],
)

control_state = {
    "dest_x": 0.0,
    "dest_y": 0.0,
    "base_speed": config.BASE_SPEED,
    "turn_speed": config.TURN_SPEED,
    "updated": False,
}

state_lock = threading.Lock()

# ---------- API models ----------
class XYCommand(BaseModel):
    x: float
    y: float

class SpeedCommand(BaseModel):
    base_speed: float
    turn_speed: float

# ---------- API endpoints ----------
@app.post("/command/xy")
def set_xy(cmd: XYCommand):
    with state_lock:
        control_state["dest_x"] = cmd.x
        control_state["dest_y"] = cmd.y
        control_state["updated"] = True
    return {"status": "ok"}

@app.post("/config/speed")
def set_speed(cmd: SpeedCommand):
    with state_lock:
        control_state["base_speed"] = cmd.base_speed
        control_state["turn_speed"] = cmd.turn_speed
    return {"status": "ok"}

@app.get("/state")
def get_state():
    with state_lock:
        return control_state.copy()

# ---------- NEW: movement test ----------
@app.post("/test/movement")
def test_movement():
    # run in a thread so API doesn’t block
    threading.Thread(
        target=movement_test.run_movement_test,
        daemon=True
    ).start()

    return {"status": "movement test started"}
