from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import config
import movement_test   # 👈 import test
from interrupt import STOP_EVENT
import motor_helper as mh
from sdr_control import PlutoSDR
from fastapi import HTTPException
import txGPS
from main import RoverController




app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_methods=["*"],
    allow_headers=["*"],
)

# control_state = {
#     "dest_x": 0.0,
#     "dest_y": 0.0,
#     "base_speed": config.BASE_SPEED,
#     "turn_speed": config.TURN_SPEED,
#     "updated": False,
#     "stop": False,   
# }


# state_lock = threading.Lock()
from sharedstate import control_state, state_lock

# ---------- API models ----------
class XYCommand(BaseModel):
    x: float
    y: float

class SpeedCommand(BaseModel):
    base_speed: float
    turn_speed: float

# ---------- SDR state ----------
sdr_instances = {}   # rover_id -> PlutoSDR
sdr_lock = threading.Lock()


class SDRConnectCommand(BaseModel):
    rover_id: str
    uri: str


class SDRConfig(BaseModel):
    rover_id: str
    direction: str        # "rx" or "tx"

    frequency: int        # MHz
    bandwidth: int        # MHz
    sample_rate: int      # MS/s

    gain_mode: str | None = None
    gain: int | None = None


# ---------- Navigation state ----------
nav_thread = None
nav_controller = None
nav_lock = threading.Lock()

class NavStartCommand(BaseModel):
    dest_x: float
    dest_y: float
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

@app.post("/test/movement")
def test_movement():
    STOP_EVENT.clear()

    threading.Thread(
        target=movement_test.run_movement_test,
        daemon=True
    ).start()

    return {"status": "movement test started"}


# -- FORCE STOP 
@app.post("/stop")
def force_stop():
    STOP_EVENT.set()

    with state_lock:
        control_state["stop"] = True
        control_state["updated"] = False

    mh.stop()
    return {"status": "INTERRUPT: STOP"}


@app.post("/sdr/connect")
def connect_sdr(cmd: SDRConnectCommand):
    with sdr_lock:
        if cmd.rover_id in sdr_instances:
            return {"status": "already connected"}

        try:
            sdr_instances[cmd.rover_id] = PlutoSDR(uri=cmd.uri)
            return {"status": "connected", "rover_id": cmd.rover_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        


@app.post("/sdr/config")
def configure_sdr(cfg: SDRConfig):
    if cfg.rover_id not in sdr_instances:
        raise HTTPException(status_code=400, detail="SDR not connected")

    sdr = sdr_instances[cfg.rover_id]
    HZ = 1_000_000

    with sdr_lock:
        sdr.set_sample_rate(cfg.sample_rate * HZ)

        if cfg.direction == "rx":
            sdr.set_rx_frequency(cfg.frequency * HZ)
            sdr.set_rx_bandwidth(cfg.bandwidth * HZ)

            if cfg.gain_mode:
                if cfg.gain_mode not in {"manual", "fast_attack", "slow_attack", "hybrid"}:
                    raise HTTPException(400, "Invalid gain mode")

                sdr.set_rx_gain_mode(cfg.gain_mode)

                if cfg.gain_mode == "manual" and cfg.gain is not None:
                    sdr.set_rx_gain(cfg.gain)

        elif cfg.direction == "tx":
            sdr.set_tx_frequency(cfg.frequency * HZ)
            sdr.set_tx_bandwidth(cfg.bandwidth * HZ)

            if cfg.gain is not None:
                sdr.set_tx_gain(cfg.gain)

        else:
            raise HTTPException(status_code=400, detail="Invalid direction")

    return {"status": "configured"}


@app.get("/sdr/status/{rover_id}")
def sdr_status(rover_id: str):
    if rover_id not in sdr_instances:
        raise HTTPException(status_code=400, detail="SDR not connected")

    sdr = sdr_instances[rover_id]

    with sdr_lock:
        return {
            "rx": sdr.get_rx_parameters(),
            "tx": sdr.get_tx_parameters(),
        }


@app.post("/sdr/disconnect/{rover_id}")
def disconnect_sdr(rover_id: str):
    with sdr_lock:
        if rover_id in sdr_instances:
            sdr_instances[rover_id].close()
            del sdr_instances[rover_id]

    return {"status": "disconnected"}


import txGPS

@app.post("/sdr/txgps")
def trigger_tx_gps():
    try:
        # Directly create SDR and transmit
        sdr = PlutoSDR(uri="ip:192.168.2.1")

        # If needed, set TX params here (optional)
        # sdr.set_tx_frequency(...)
        # sdr.set_tx_sample_rate(...)
        # sdr.set_tx_bandwidth(...)
        # sdr.set_tx_gain(...)

        txGPS.transmit_once(sdr)

        sdr.close()

        return {"status": "GPS transmission sent"}

    except Exception as e:
        print("TX ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Navigation Endpoints ----------

@app.post("/nav/start")
def start_navigation(cmd: NavStartCommand):
    global nav_thread, nav_controller

    with nav_lock:
        if nav_thread and nav_thread.is_alive():
            return {"status": "Navigation already running"}

        # Update shared control state
        with state_lock:
            control_state["dest_x"] = cmd.dest_x
            control_state["dest_y"] = cmd.dest_y
            control_state["base_speed"] = cmd.base_speed
            control_state["turn_speed"] = cmd.turn_speed
            control_state["updated"] = True
            control_state["stop"] = False

        # Clear interrupt flag
        STOP_EVENT.clear()

        # Create controller
        nav_controller = RoverController()

        def run_nav():
            try:
                nav_controller.run()
            except Exception as e:
                print("Navigation error:", e)
                mh.stop()

        nav_thread = threading.Thread(
            target=run_nav,
            daemon=True
        )
        nav_thread.start()

    return {"status": "navigation started"}

@app.post("/nav/stop")
def stop_navigation():
    global nav_controller

    STOP_EVENT.set()

    with state_lock:
        control_state["updated"] = False
        control_state["stop"] = True

    mh.stop()

    return {"status": "navigation stopped"}


@app.get("/")
def health():
    return {"status": "online"}
