from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import config
import movement_test   
from interrupt import STOP_EVENT
import motor_helper as mh
from sdr_control import PlutoSDR
from fastapi import HTTPException
import txGPS
import gpsd
from main import RoverController
from gps_test import get_current_gps
import numpy as np
import json


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_methods=["*"],
    allow_headers=["*"],
)


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

# ---------- RX buffer state ----------
rx_buffers = {}        # rover_id -> list of messages
rx_seq = {}            # rover_id -> last sequence number

gps_tx_threads = {}     # rover_id -> thread
gps_tx_flags = {}       # rover_id -> stop event


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

class TxGPSCommand(BaseModel):
    rover_id: str

# ---------- Navigation state ----------
nav_thread = None
nav_controller = None
nav_lock = threading.Lock()

class NavStartCommand(BaseModel):
    dest_x: float
    dest_y: float
    base_speed: float
    turn_speed: float

class MissionCommand(BaseModel):
    waypoints: list[XYCommand]
    base_speed: float
    turn_speed: float


def fsk_demodulate(iq_samples, sps=100, sample_rate=4000000):

    num_bits = len(iq_samples) // sps
    bits = []

    for i in range(num_bits):
        segment = iq_samples[i*sps:(i+1)*sps]

        fft = np.fft.fft(segment)
        freqs = np.fft.fftfreq(len(segment), 1/sample_rate)

        pos_freqs = freqs[:len(freqs)//2]
        pos_fft = np.abs(fft[:len(fft)//2])

        peak_idx = np.argmax(pos_fft)
        peak_freq = abs(pos_freqs[peak_idx])

        if abs(peak_freq - 50000) < abs(peak_freq - 150000):
            bits.append(0)
        else:
            bits.append(1)

    return np.array(bits, dtype=np.uint8)

def bits_to_string(bits):

    chars = []

    for i in range(0, len(bits), 8):

        if i + 8 > len(bits):
            break

        byte_bits = bits[i:i+8]

        byte_val = 0

        for j, bit in enumerate(byte_bits):
            byte_val |= (bit << (7-j))

        if 32 <= byte_val <= 126:
            chars.append(chr(byte_val))

    return ''.join(chars)

# ---------- API endpoints ----------

import time

def gps_tx_loop(rover_id: str):
    stop_event = gps_tx_flags[rover_id]
    sdr = sdr_instances[rover_id]

    print(f"[GPS TX] Started for {rover_id}")

    while not stop_event.is_set():
        try:
            with sdr_lock:
                txGPS.transmit_once(sdr)
        except Exception as e:
            print("GPS TX loop error:", e)

        stop_event.wait(10)   # transmit every 10 seconds

    print(f"[GPS TX] Stopped for {rover_id}")
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


#FORCE STOP 
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

            # START RX LOOP
            threading.Thread(
                target=sdr_rx_loop,
                args=(cfg.rover_id,),
                daemon=True
            ).start()

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

@app.get("/sdr/buffer/{rover_id}")
def get_buffer(rover_id: str, since_seq: int = 0):

    if rover_id not in rx_buffers:
        return {"messages": [], "max_seq": 0}

    messages = [m for m in rx_buffers[rover_id] if m["seq"] > since_seq]

    max_seq = rx_seq.get(rover_id, 0)

    return {
        "messages": messages,
        "max_seq": max_seq
    }

def push_rx_message(rover_id: str, data: str):

    if rover_id not in rx_buffers:
        rx_buffers[rover_id] = []
        rx_seq[rover_id] = 0

    rx_seq[rover_id] += 1

    msg = {
        "seq": rx_seq[rover_id],
        "data": data,
        "timestamp": time.time(),
        "length": len(data),
        "direction": "rx"
    }

    rx_buffers[rover_id].append(msg)

    # keep buffer size manageable
    if len(rx_buffers[rover_id]) > 200:
        rx_buffers[rover_id].pop(0)
    
import txGPS


@app.post("/sdr/txgps")
def trigger_tx_gps(cmd: TxGPSCommand):

    if cmd.rover_id not in sdr_instances:
        raise HTTPException(status_code=400, detail="SDR not connected")

    sdr = sdr_instances[cmd.rover_id]

    try:
        with sdr_lock:
            txGPS.transmit_once(sdr)

        
        push_rx_message(cmd.rover_id, "GPS packet transmitted")

        return {"status": "GPS transmission sent"}

    except Exception as e:
        print("TX ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/sdr/txgps/start")
def start_gps_tx(cmd: TxGPSCommand):
    if cmd.rover_id not in sdr_instances:
        raise HTTPException(400, "SDR not connected")

    if cmd.rover_id in gps_tx_threads:
        return {"status": "already running"}

    stop_event = threading.Event()
    gps_tx_flags[cmd.rover_id] = stop_event

    thread = threading.Thread(
        target=gps_tx_loop,
        args=(cmd.rover_id,),
        daemon=True
    )

    gps_tx_threads[cmd.rover_id] = thread
    thread.start()

    return {"status": "GPS TX started"}
def string_to_bits(text):
    bits = []
    for char in text:
        byte = ord(char)
        for i in range(8):
            bits.append((byte >> (7-i)) & 1)
    return np.array(bits, dtype=np.uint8)
GPS_PATTERN = '{"type":"gps"'
GPS_PATTERN_BITS = string_to_bits(GPS_PATTERN)
GPS_PATTERN_LEN = len(GPS_PATTERN_BITS)
def sdr_rx_loop(rover_id: str):

    sdr = sdr_instances[rover_id]

    print(f"[SDR RX] Started for {rover_id}")

    sdr.setup_rx_buffer(131072)

    search_pattern = '{"type":"gps"'
    pattern_bits = string_to_bits(search_pattern)
    pattern_len = len(pattern_bits)

    while True:

        try:

            with sdr_lock:
                samples = sdr.receive_samples()

            if samples is None or len(samples) == 0:
                continue

            gps_found = False

            # Demodulate samples into bits
            bits = fsk_demodulate(samples, sps=100, sample_rate=4000000)

            best_match = 0
            best_start = None

            # Search for GPS JSON pattern in bitstream
            for start in range(len(bits) - pattern_len):

                test_bits = bits[start:start + pattern_len]

                matches = np.sum(test_bits == pattern_bits)

                if matches > best_match:
                    best_match = matches
                    best_start = start

                # If match quality good enough (~85%)
                if matches >= int(pattern_len * 0.85):

                    # Decode possible JSON message
                    message_bits = bits[start:start + 640]   # ~80 chars
                    message = bits_to_string(message_bits)

                    if '}' in message:

                        json_str = message[:message.index('}') + 1]

                        try:

                            data = json.loads(json_str)

                            lat = data["lat"]
                            lon = data["lon"]

                            msg = {
                                "type": "gps",
                                "lat": lat,
                                "lon": lon,
                                "time": data.get("t")
                            }

                            push_rx_message(
                                rover_id,
                                json.dumps(msg)
                            )

                            print(f"[GPS RX] {lat:.6f}, {lon:.6f}")

                            gps_found = True
                            break

                        except Exception as e:
                            print("GPS parse error:", e)

            if not gps_found:

                push_rx_message(
                    rover_id,
                    f"RX {len(samples)} samples | best match {best_match}/{pattern_len}"
                )

        except Exception as e:
            print("RX error:", e)

        time.sleep(0.1)

    

@app.post("/sdr/txgps/stop")
def stop_gps_tx(cmd: TxGPSCommand):
    if cmd.rover_id not in gps_tx_threads:
        return {"status": "not running"}

    gps_tx_flags[cmd.rover_id].set()

    del gps_tx_threads[cmd.rover_id]
    del gps_tx_flags[cmd.rover_id]

    return {"status": "GPS TX stopped"}


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

@app.post("/nav/mission")
def run_mission(cmd: MissionCommand):

    print("MISSION RECEIVED:", cmd.waypoints)

    if not cmd.waypoints:
        return {"status": "no waypoints"}

    def mission_thread():

        # Reset stop flags
        STOP_EVENT.clear()

        with state_lock:
            control_state["stop"] = False

        controller = RoverController()

        for wp in cmd.waypoints:

            if STOP_EVENT.is_set():
                break

            print(f"Navigating to waypoint: ({wp.x}, {wp.y})")

            with state_lock:
                control_state["dest_x"] = wp.x
                control_state["dest_y"] = wp.y
                control_state["base_speed"] = cmd.base_speed
                control_state["turn_speed"] = cmd.turn_speed
                control_state["updated"] = True
                control_state["stop"] = False

            controller.nav.set_destination(wp.x, wp.y)

            controller.run()

        mh.stop()
        print("Mission complete.")

    threading.Thread(target=mission_thread, daemon=True).start()

    return {"status": "mission started"}

@app.get("/nav/state")
def nav_state():
    if nav_controller is None:
        return {"x": 0, "y": 0, "heading": 0}

    return {
        "x": nav_controller.nav.x,
        "y": nav_controller.nav.y,
        "heading": nav_controller.nav.get_heading_error()
    }

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


@app.get("/gps/current")
def get_gps():
    packet = gpsd.get_current()

    return {
        "lat": packet.lat,
        "lon": packet.lon,
        "mode": packet.mode,
        "time": packet.time,     
        "track": packet.track,
        "speed": packet.hspeed,
        "satellites": packet.sats
    }