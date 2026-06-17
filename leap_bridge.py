"""
Bridges the native Ultraleap Gemini LeapC library to the legacy v7.json
WebSocket protocol expected by zakaton's Leap-Motion-Web-SDK (leap-motion.js).

Ultraleap Gemini (v5) ships no WebSocket server, so the browser SDK can
never connect to ws://localhost:6437/v7.json on its own. This script polls
the native LeapC connection directly via ctypes and re-serves the data
over that same WebSocket URL/protocol shape.

Run with python3.11 (the only interpreter on this machine with both a
working ctypes load of libLeapC.6.dylib and the `websockets` package):

    python3.11 leap_bridge.py
"""
import asyncio
import ctypes
import json
import math
import time

import websockets

DYLIB_PATH = "/Applications/Ultraleap Hand Tracking.app/Contents/LeapSDK/lib/libLeapC.6.dylib"

# ---- ctypes struct definitions (mirroring LeapC.h) ------------------------

# LeapC.h wraps this whole section in `#pragma pack(1)` (byte-packed, no
# compiler-inserted padding), so every Structure here must match with _pack_ = 1
# or field offsets silently drift and reads land on garbage/adjacent fields.

class LEAP_VECTOR(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float), ("z", ctypes.c_float)]

class LEAP_QUATERNION(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float),
                ("z", ctypes.c_float), ("w", ctypes.c_float)]

class LEAP_BONE(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("prev_joint", LEAP_VECTOR), ("next_joint", LEAP_VECTOR),
                ("width", ctypes.c_float), ("rotation", LEAP_QUATERNION)]

class LEAP_DIGIT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("finger_id", ctypes.c_int32), ("bones", LEAP_BONE * 4),
                ("is_extended", ctypes.c_uint32)]

class LEAP_PALM(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("position", LEAP_VECTOR), ("stabilized_position", LEAP_VECTOR),
                ("velocity", LEAP_VECTOR), ("normal", LEAP_VECTOR),
                ("width", ctypes.c_float), ("direction", LEAP_VECTOR),
                ("orientation", LEAP_QUATERNION)]

class LEAP_HAND(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("id", ctypes.c_uint32), ("flags", ctypes.c_uint32),
                ("type", ctypes.c_int32), ("confidence", ctypes.c_float),
                ("visible_time", ctypes.c_uint64), ("pinch_distance", ctypes.c_float),
                ("grab_angle", ctypes.c_float), ("pinch_strength", ctypes.c_float),
                ("grab_strength", ctypes.c_float), ("palm", LEAP_PALM),
                ("digits", LEAP_DIGIT * 5), ("arm", LEAP_BONE)]

class LEAP_FRAME_HEADER(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("reserved", ctypes.c_void_p), ("frame_id", ctypes.c_int64),
                ("timestamp", ctypes.c_int64)]

class LEAP_TRACKING_EVENT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("info", LEAP_FRAME_HEADER), ("tracking_frame_id", ctypes.c_int64),
                ("nHands", ctypes.c_uint32), ("pHands", ctypes.POINTER(LEAP_HAND)),
                ("framerate", ctypes.c_float)]

class LEAP_CONNECTION_MESSAGE(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("size", ctypes.c_uint32), ("type", ctypes.c_int32),
                ("pointer", ctypes.c_void_p)]

eLeapRS_Success = 0x00000000
eLeapRS_NotConnected = 0xE2010002  # informational only
eLeapEventType_Tracking = 0x100

LEAP_CONNECTION = ctypes.c_void_p

lib = ctypes.CDLL(DYLIB_PATH)

lib.LeapCreateConnection.argtypes = [ctypes.c_void_p, ctypes.POINTER(LEAP_CONNECTION)]
lib.LeapCreateConnection.restype = ctypes.c_int32

lib.LeapOpenConnection.argtypes = [LEAP_CONNECTION]
lib.LeapOpenConnection.restype = ctypes.c_int32

lib.LeapPollConnection.argtypes = [LEAP_CONNECTION, ctypes.c_uint32,
                                    ctypes.POINTER(LEAP_CONNECTION_MESSAGE)]
lib.LeapPollConnection.restype = ctypes.c_int32

lib.LeapCloseConnection.argtypes = [LEAP_CONNECTION]
lib.LeapCloseConnection.restype = None

# ---- LeapC -> legacy v7.json translation -----------------------------------

def vec_to_list(v):
    return [v.x, v.y, v.z]

def quat_to_euler_rpy(q):
    """Returns (roll, pitch, yaw) in radians from a LEAP_QUATERNION."""
    x, y, z, w = q.x, q.y, q.z, q.w
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    sinp = 2 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))
    pitch = math.asin(sinp)
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return roll, pitch, yaw

DIGIT_NAMES = ["thumb", "index", "middle", "ring", "pinky"]
MAX_FINGER_REACH_MM = 120.0  # rough normalization constant for tip-to-palm distance

def digit_to_json(digit, name, palm_position):
    tip = digit.bones[3].next_joint  # distal bone's far joint = fingertip
    dx = tip.x - palm_position.x
    dy = tip.y - palm_position.y
    dz = tip.z - palm_position.z
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    extension = max(0.0, min(1.0, dist / MAX_FINGER_REACH_MM))
    return {
        "name": name,
        "extended": bool(digit.is_extended),
        "extension": extension,
        "tip": [tip.x, tip.y, tip.z],
    }

def hand_to_json(hand: LEAP_HAND, hand_index: int):
    palm = hand.palm
    roll, pitch, yaw = quat_to_euler_rpy(palm.orientation)
    fingers = [digit_to_json(hand.digits[i], DIGIT_NAMES[i], palm.position) for i in range(5)]
    return {
        "id": hand.id,
        "type": "right" if hand.type == 1 else "left",
        "confidence": hand.confidence,
        "grabStrength": hand.grab_strength,
        "grabAngle": hand.grab_angle,
        "pinchStrength": hand.pinch_strength,
        "pinchDistance": hand.pinch_distance,
        "palmPosition": vec_to_list(palm.position),
        "stabilizedPalmPosition": vec_to_list(palm.stabilized_position),
        "palmVelocity": vec_to_list(palm.velocity),
        "palmNormal": vec_to_list(palm.normal),
        "palmWidth": palm.width,
        "direction": vec_to_list(palm.direction),
        "r": roll, "pitch": pitch, "yaw": yaw,
        "armBasis": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "armWidth": hand.arm.width,
        "elbow": vec_to_list(hand.arm.prev_joint),
        "wrist": vec_to_list(hand.arm.next_joint),
        "timeVisible": hand.visible_time / 1e6,
        "fingers": fingers,
    }

def tracking_event_to_json(evt: LEAP_TRACKING_EVENT, hand_structs):
    hands = [hand_to_json(h, i) for i, h in enumerate(hand_structs)]
    return {
        "currentFrameRate": evt.framerate,
        "id": evt.tracking_frame_id,
        "timestamp": evt.info.timestamp,
        "hands": hands,
        "pointables": [],
    }

# ---- WebSocket server --------------------------------------------------

clients = set()

async def handler(websocket):
    clients.add(websocket)
    print(f"[bridge] browser connected ({len(clients)} total)")
    try:
        await websocket.send(json.dumps({"version": 7, "serviceVersion": "5.0.0-bridge"}))
        async for _ in websocket:
            pass
    finally:
        clients.discard(websocket)
        print(f"[bridge] browser disconnected ({len(clients)} total)")

async def broadcast(message: str):
    if not clients:
        return
    dead = []
    for ws in list(clients):
        try:
            await ws.send(message)
        except websockets.exceptions.ConnectionClosed:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)

async def leap_poll_loop():
    connection = LEAP_CONNECTION()
    rs = lib.LeapCreateConnection(None, ctypes.byref(connection))
    if rs != eLeapRS_Success:
        raise RuntimeError(f"LeapCreateConnection failed: {rs:#x}")
    rs = lib.LeapOpenConnection(connection)
    if rs != eLeapRS_Success:
        raise RuntimeError(f"LeapOpenConnection failed: {rs:#x}")
    print("[bridge] LeapC connection open, polling for tracking frames...")

    msg = LEAP_CONNECTION_MESSAGE()
    last_log = 0
    try:
        while True:
            rs = lib.LeapPollConnection(connection, 1000, ctypes.byref(msg))
            if rs == eLeapRS_Success and msg.type == eLeapEventType_Tracking and msg.pointer:
                # Deep-copy the event (and the hand array it points to) immediately,
                # before yielding control, since LeapC may recycle this buffer on
                # its own background thread as soon as we return from this poll.
                src = ctypes.cast(msg.pointer, ctypes.POINTER(LEAP_TRACKING_EVENT))
                evt = LEAP_TRACKING_EVENT()
                ctypes.memmove(ctypes.byref(evt), src, ctypes.sizeof(LEAP_TRACKING_EVENT))
                phands_addr = ctypes.cast(evt.pHands, ctypes.c_void_p).value
                hand_structs = []
                if evt.nHands and phands_addr:
                    hand_buf = (LEAP_HAND * evt.nHands)()
                    ctypes.memmove(hand_buf, evt.pHands, ctypes.sizeof(LEAP_HAND) * evt.nHands)
                    hand_structs = list(hand_buf)

                payload = tracking_event_to_json(evt, hand_structs)
                await broadcast(json.dumps(payload))
                now = time.time()
                if now - last_log > 2:
                    print(f"[bridge] frame: {evt.nHands} hand(s), {evt.framerate:.1f} fps")
                    last_log = now
            await asyncio.sleep(0)
    finally:
        lib.LeapCloseConnection(connection)

async def main():
    server = await websockets.serve(handler, "localhost", 6437)
    print("[bridge] WebSocket server listening on ws://localhost:6437/v7.json")
    await asyncio.gather(leap_poll_loop(), server.wait_closed())

if __name__ == "__main__":
    asyncio.run(main())
