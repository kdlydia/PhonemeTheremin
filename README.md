# Phoneme Theremin

The original intent was a speech therapy tool: a device where patients could see and feel how consonant place and vowel quality map to hand position, making articulation tangible. Time constraints made that scope unrealistic. What exists instead is a phoneme theremin: an instrument that plays the building blocks of speech rather than musical notes.

Two hands control a physically modeled vocal tract in real time. A Leap Motion controller reads hand position, wrist angle, finger extension, grab speed, and inter-hand distance. These feed into Pink Trombone, a browser-based vocal tract synthesizer, and shape pitch, vowel quality, consonant place, plosive bursts, fricative noise, breathiness, and volume.

Two versions are included. v1 uses one hand for basic vowel and consonant control. v2 splits the hands: right hand controls pitch and vowels, left hand controls consonants using place of articulation, fast-grab plosive bursts, and per-finger fricatives.

---

## Requirements

**Hardware**

- Leap Motion Controller (any generation supported by Ultraleap Gemini v5)
- Mac running macOS 12 or later (tested on macOS 15)
- Speakers or headphones
- USB-A port or adapter

**Software**

- Ultraleap Hand Tracking software, Gemini v5. Download from ultraleap.com. Must be running before anything else.
- Python 3.11
- Python websockets package
- Google Chrome

---

## Install

Run this once after cloning:

```
pip3.11 install websockets
```

No other installation is needed.

---

## Setup

**Step 1. Clone the repository**

```
git clone https://github.com/kdlydia/hand-vocal-synth
cd hand-vocal-synth
```

**Step 2. Start the Ultraleap tracking service**

Open the Ultraleap Hand Tracking app. Its icon appears in the menu bar when running. Plug in the Leap Motion controller. The icon changes when a device is detected.

**Step 3. Start the bridge**

Open a terminal and run:

```
python3.11 leap_bridge.py
```

Leave this terminal open. It prints the frame rate when hands are detected. This process translates native tracking data from the Ultraleap C library into the WebSocket protocol the browser expects. It must keep running for the piece to work.

**Step 4. Start a local HTTP server**

Open a second terminal and run:

```
python3.11 -m http.server 8765
```

Leave this open too.

**Step 5. Open Chrome**

Navigate to one of these:

```
http://localhost:8765/index.html        (v1, single hand)
http://localhost:8765/index_v2.html     (v2, two hands)
```

**Step 6. Allow local network access in Chrome (first time only)**

Chrome blocks pages from connecting to localhost by default. Go to:

```
chrome://settings/content/localNetworkAccess
```

Add `http://localhost:8765` to the allowed list. Without this the piece shows "Disconnected" and produces no sound.

If Chrome shows a permission prompt when the page loads, click Allow. That also works.

**Step 7. Start audio**

Click anywhere on the synthesizer canvas. Chrome requires a user gesture before playing audio. After clicking, hold one or both hands above the Leap Motion controller. Sound starts immediately.

---

## Daily startup (gallery use)

Run these two commands, then open Chrome and leave it. No attendant needed after that.

```
python3.11 leap_bridge.py &
python3.11 -m http.server 8765
```

Open `http://localhost:8765/index_v2.html`, click the canvas once, go full screen.

---

## Gesture reference

### v1, single hand

| Gesture | Effect |
|---|---|
| Hand height 50 to 350 mm | Pitch, F2 to F4, two octaves |
| Palm X left to right | Vowel back to front (u/o to i/e) |
| Wrist roll, palm down to sideways | Mouth open to closed (a to i/u) |
| Grab strength | Oral constriction |
| Pinch strength | Velum opening, nasal resonance |

### v2, two hands

**Right hand controls vowels and pitch.**

| Gesture | Effect |
|---|---|
| Height 50 to 350 mm | Pitch F2 to F4 |
| Palm X | Vowel front/back |
| Wrist roll | Mouth openness |
| Pinch | Nasal resonance |

**Left hand controls consonants.**

| Gesture | Effect |
|---|---|
| Palm X position | Place of articulation, glottal to bilabial |
| Fast grab and release | Plosive burst at current place |
| Index finger extended | Alveolar fricative, S region |
| Middle finger extended | Postalveolar fricative, SH region |
| Ring finger extended | Velar fricative, K region |
| Pinky extended | Pharyngeal/glottal fricative, H region |
| Finger spread, index to pinky | Breathiness, aspiration |

**Both hands.**

| Gesture | Effect |
|---|---|
| Distance between palms | Output volume. Close is quiet, far is loud. |

---

## Artistic concept

The human voice produces speech by changing the shape of a continuous air column running from the lungs through the throat and mouth. Different mouth shapes, tongue positions, and lip configurations produce different sounds. This piece makes that mechanism visible and directly controllable by hand.

The right hand sets vowel quality. Moving it left and right shifts the tongue front or back in the simulated mouth. Rolling the wrist opens or closes the oral aperture. Raising the hand raises pitch. These are continuous, exploratory controls.

The left hand handles consonants. Its horizontal position sets where in the mouth a constriction occurs, from the back of the throat to the lips. Individual fingers trigger sustained fricative noise at specific places: the index finger produces alveolar friction at the S region, the middle finger produces postalveolar friction at SH, the ring finger at the velar K region, the pinky at the pharyngeal/glottal H region. These positions correspond directly to the IPA consonant chart. A fast grab and release produces a plosive burst at whatever place the palm currently specifies.

The piece is not a musical instrument in the conventional sense. There is no melody, no rhythm, no score. The output is raw speech sound without language. A visitor who listens before moving will hear more than one who moves first.

---

## Intended audience

People with no musical training who are curious about how speech sounds are made. The piece does not require knowing music theory or phonetics. The connection between hand position and vocal output should become clear through exploration, not instruction.

Not for people who need a goal or a score.

---

## What I want / what I do not want

**Want:**
- Visitor discovers more than one gesture on their own
- The plosive burst surprises them when they find it
- Visitor starts thinking about how consonants and vowels are physically produced
- Someone with no musical background makes something they find interesting
- Visitor listens before they move

**Do not want:**
- Visitor waves hands without listening to what changes
- Gallery ambient noise drowning out the fricatives, which are quiet by design
- An attendant explaining gestures before the visitor tries
- Visitor looking for a correct answer or trying to play a melody

**Acceptable:**
- Visitor gives up quickly
- Two visitors taking turns and comparing what they produce
- Visitor makes sounds that are not speech-like at all

---

## Gallery installation

**Space**

A separate small room or alcove with enough acoustic separation that the fricative sounds are audible at one meter. Open gallery floors with ambient crowd noise are not suitable. The fricative consonants are physically quiet and disappear if the room is loud.

**Physical setup**

- Leap Motion controller on a dark matte plinth, surface at 950 mm above floor
- Mac mini or laptop inside or behind the plinth, not visible
- One monitor, 24 to 32 inches, showing the Pink Trombone throat visualization, mounted at eye level
- Two speakers at ear level aimed at the visitor
- One small card on the plinth: "Place your hands above the sensor." No other instructions.

---

## Original contributions

**leap_bridge.py**

Ultraleap Gemini v5 ships no WebSocket server. The browser SDK expects one at ws://localhost:6437/v7.json. This script calls the native LeapC C library directly via Python ctypes, defines all tracking structs to match the C ABI (byte-packed, requiring _pack_ = 1 in every ctypes Structure or field reads return garbage), and re-serves frame data in the legacy v7.json protocol. Nothing equivalent exists as a published tool.

**Gesture-to-phonetics mapping**

The assignment of hand geometry to vocal tract parameters is the core of this project. The four non-thumb fingers trigger fricative constrictions at linguistically specific places. Grab velocity triggers plosive bursts rather than sustained closures. Finger spread modulates glottal tenseness for breathiness. Inter-hand distance scales output gain. These decisions map hand anatomy onto the IPA consonant chart.

---

## Attribution

- Pink Trombone vocal synthesizer by Neil Thapen
- Leap Motion Web SDK by Zackary Shorr (zakaton), MIT license
- Max Pink Trombone by Yonatan Rozin

---

## Files

```
leap_bridge.py         native LeapC to WebSocket bridge, run this first
index.html             v1, single-hand
index_v2.html          v2, two-hand gesture vocabulary
leap-motion.js         compiled Leap Motion Web SDK
Leap-Motion-Web-SDK/   SDK source, MIT license
```
