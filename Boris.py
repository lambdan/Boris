import json
import sys, os, time, datetime
from tkinter import CURRENT
from webbrowser import get
from pynput import mouse
import mss, mss.tools
import numpy, cv2

DATA = {
    "capture": {
        "tl": None,
        "br": None,
    },
    "levels": {},
    "last_played": None,
}


SESSION = {
    "durationAtStart": 0,
    "attemptsAtStart": 0,
    "started": None,
    "attempts": 0
}

SAVE_FILE = "./Boris.json"
SCREENS_FOLDER = "./screens/"
AUTO_SAVE_FREQ = 10 # auto save every n attempts
WAIT_DELAY = 16 # 16 ms = 60 FPS
DOWNSCALE_RES = (200,150) # as low as 40,30 has worked


THRESHOLD = 0.8


LAST_SAVE = None
LAST_CLICKED_COORD = None
IS_PAUSED = False
LAST_SCREEN = None
HISTORY = []
RUNNING = False
PAUSE_STARTED = None
PAUSED_DURATION = 0
STATUS_MESSAGE = "HELLO!"

# font stuff
FONT = cv2.FONT_HERSHEY_DUPLEX
FONT_SCALE = 1
FONT_THICK = 2
COLOR_PAUSED = (255,255,0) # cyan
COLOR_RUNNING = (0,252,124) # bright green
COLOR_INACTIVE = (105,105,105) # grey
COLOR_REGULAR = (255,255,255) # white
COLOR_FLASH = (0,0,255) # red



def save():
    global LAST_SAVE, DATA
    if SESSION["started"]:
        DATA["levels"][CURRENT_LEVEL]["attempts"] = getTotalAttempts(CURRENT_LEVEL)
        DATA["levels"][CURRENT_LEVEL]["duration"] = getTotalDuration(CURRENT_LEVEL)
        DATA["levels"][CURRENT_LEVEL]["last_played"] = datetime.datetime.now().isoformat()
        DATA["last_played"] = CURRENT_LEVEL
    with open(SAVE_FILE, "w") as f:
        json.dump(DATA, f, indent=4)
    print("Saved data to", SAVE_FILE)
    LAST_SAVE = datetime.datetime.now()

def load():
    if not os.path.exists(SAVE_FILE):
        print("No save file found, cant load data")
        return
    global DATA
    with open(SAVE_FILE, "r") as f:
        DATA = json.load(f)


def compare_l2_norm(source, capture):
    # https://github.com/Toufool/Auto-Split/blob/master/src/compare.py
    error = cv2.norm(source, capture, cv2.NORM_L2)
    max_error = (source.size ** 0.5) * 255
    return 1 - (error/max_error)

def screenshotRegion(l,t,w,h):
    with mss.mss() as sct:
        region = {'top': t, 'left': l, 'width': w, 'height': h}
        ss = sct.grab(region)
        img = numpy.array(ss)
        return img

def formatDuration(in_secs) -> str:
    """Formats a float in seconds into HH:MM:SS.X"""
    if in_secs < 0:
        in_secs = 0
    hours = int(in_secs // 3600)
    minutes = int((in_secs % 3600) // 60)
    seconds = int(in_secs % 60)
    milliseconds = int((in_secs - int(in_secs)) * 10) # one decimal place
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds}"
    return f"{minutes:02}:{seconds:02}.{milliseconds}"


def percentage(fl):
    return str(round(fl*100, 1)) + "%"

def on_click(x, y, button, pressed):
    global LAST_CLICKED_COORD
    if pressed:
        LAST_CLICKED_COORD = (x, y)

SETTING_REGION = False
def setCaptureRegion():
    global LAST_CLICKED_COORD, SETTING_REGION
    if SETTING_REGION:
        print("Already setting capture region")
        return
    SETTING_REGION = True
    LAST_CLICKED_COORD = None
    listener = mouse.Listener(on_click=on_click)
    listener.start()

    coordsTopLeft = None
    coordsBottomRight = None
    print("Click top-left corner of game capture")
    while coordsTopLeft is None:
        if LAST_CLICKED_COORD is not None:
            coordsTopLeft = LAST_CLICKED_COORD
            LAST_CLICKED_COORD = None

    print("Click bottom-right corner of game capture")
    while coordsBottomRight is None:
        if LAST_CLICKED_COORD is not None:
            coordsBottomRight = LAST_CLICKED_COORD
            LAST_CLICKED_COORD = None
    
    DATA["capture"]["tl"] = coordsTopLeft
    DATA["capture"]["br"] = coordsBottomRight
    listener.stop()
    mouse.Listener.stop # is this necessary?
    SETTING_REGION = False
    save()

def getSessionDuration() -> float:
    """Returns the duration of the current session in seconds."""
    if SESSION["started"] is None:
        return 0.0
    pauseOffset = PAUSED_DURATION
    if IS_PAUSED:
        pauseOffset += (time.time() - PAUSE_STARTED) # type: ignore
    return time.time() - SESSION["started"] - pauseOffset

def getTotalDuration(levelName: str) -> float:
    return SESSION["durationAtStart"] + getSessionDuration()

def getSessionAttempts() -> int:
    """Returns the number of attempts in the current session."""
    return SESSION["attempts"]

def getTotalAttempts(levelName: str) -> int:
    return SESSION["attemptsAtStart"] + getSessionAttempts()

def togglePause():
    global IS_PAUSED, PAUSED_DURATION, PAUSE_STARTED, STATUS_MESSAGE
    if IS_PAUSED:
        # resume
        IS_PAUSED = False
        PAUSED_DURATION += (time.time() - PAUSE_STARTED) # type: ignore
        print("Resumed")
    else:
        # pause
        IS_PAUSED = True
        PAUSE_STARTED = time.time()
        STATUS_MESSAGE = "Paused"
        print("Paused")

def caseInsensitiveLevel(levelName: str) -> str:
    """Try finding level with different casing."""
    for l in DATA["levels"]:
        if l.lower() == levelName.lower():
            return l
    return levelName

def makeNote(level: str, note: str):
    DATA["levels"][level]["notes"].append({
        "time": datetime.datetime.now().isoformat(),
        "attempts": getTotalAttempts(level),
        "duration": getTotalDuration(level),
        "session_attempts": getSessionAttempts(),
        "session_duration": getSessionDuration(),
        "note": note
    })
    save()

####################################### starts here #############################################

load()

if DATA["capture"]["tl"] is None or DATA["capture"]["br"] is None:
    setCaptureRegion()

# easier names for the coords
pfLeft = DATA["capture"]["tl"][1]
pfTop = DATA["capture"]["tl"][0]
pfWidth = DATA["capture"]["br"][0]-DATA["capture"]["tl"][0]
pfHeight = DATA["capture"]["br"][1]-DATA["capture"]["tl"][1]

# prepare images 
BLACK_FRAME = cv2.resize(cv2.cvtColor(cv2.imread("black.png"), cv2.COLOR_BGR2GRAY), DOWNSCALE_RES) 
OHMSS_FRAME = cv2.resize(cv2.cvtColor(cv2.imread("ohmss.png"), cv2.COLOR_BGR2GRAY), DOWNSCALE_RES)

def setLevel():
    global CURRENT_LEVEL
    print("Enter level to play")
    CURRENT_LEVEL = input("Level: ")
    CURRENT_LEVEL = caseInsensitiveLevel(CURRENT_LEVEL)
    if CURRENT_LEVEL not in DATA["levels"]:
        DATA["levels"][CURRENT_LEVEL] = {
            "attempts": 0,
            "duration": 0,
            "last_played": None
        }
    DATA["last_played"] = CURRENT_LEVEL


def runSessionLoop():
    global RUNNING, IS_PAUSED, PAUSED_DURATION, PAUSE_STARTED, STATUS_MESSAGE, CURRENT_LEVEL, HISTORY

    while RUNNING:
        ### input handling
        k = cv2.waitKey( int(WAIT_DELAY) ) # requires int
        if k == ord("q"): # press q to quit
            cv2.destroyAllWindows()
            sys.exit(0)
            break
        elif k == ord("s"):
            save()
        elif k == ord("p"):
            togglePause()
        elif k == ord("g"):
            setCaptureRegion()
        elif k == ord("l"):
            DATA["last_played"] = None
            RUNNING = False # break the loop
            break
        elif k == ord("n"):
            makeNote(CURRENT_LEVEL, input("Enter note: "))

        status_view = numpy.zeros((500,500,3), numpy.uint8)
        
        if not IS_PAUSED:
            game_capture = screenshotRegion(pfTop, pfLeft, pfWidth, pfHeight)
            game_comp = cv2.resize( cv2.cvtColor(game_capture, cv2.COLOR_BGR2GRAY ), DOWNSCALE_RES )
            cv2.imshow("capture region", game_comp) 

            mostLikely = (0, "?")

            # compare against black
            black_sim = compare_l2_norm(game_comp, BLACK_FRAME)
            ohmss_sim = compare_l2_norm(game_comp, OHMSS_FRAME)
            mostLikely = (ohmss_sim, "OHMSS")

            if black_sim > 0.97 and black_sim > mostLikely[0]:
                mostLikely = [black_sim, "Black"]
            # no good match on anything, probably in-game then
            elif mostLikely[0] < THRESHOLD:
                mostLikely = [0.0, "In-game"]

            
            HISTORY.append(mostLikely[1])
            if len(HISTORY) > 10: 
                HISTORY.pop(0)

            if len(HISTORY) < 3:
                # not enough history to make a decision
                continue
        
            if HISTORY[-1] == "Black" and HISTORY[-2] == "OHMSS":
                # OHMSS -> Black == New attempt (or console shutdown)
                SESSION["attempts"] += 1

        timerColor = COLOR_PAUSED if IS_PAUSED else COLOR_RUNNING

        # title
        cv2.putText(status_view, CURRENT_LEVEL, (10,30), FONT, FONT_SCALE, (255,255,255), FONT_THICK, cv2.LINE_AA)

        if IS_PAUSED:
            cv2.putText(status_view, "PAUSED", (10,310), FONT, FONT_SCALE * 1.5, COLOR_PAUSED, FONT_THICK, cv2.LINE_AA)

        cv2.putText(status_view, "Session", (10,90), FONT, 1, (0,255,255), FONT_THICK, cv2.LINE_AA)
        cv2.putText(status_view, "Attempts: " + str(SESSION["attempts"]), (10,120), FONT, 0.8, COLOR_REGULAR, 1, cv2.LINE_AA)
        cv2.putText(status_view, formatDuration(getSessionDuration()), (10,150), FONT, 0.8, timerColor, 1, cv2.LINE_AA)

        cv2.putText(status_view, "Total", (10,200), FONT, 1, (0,128,255), FONT_THICK, cv2.LINE_AA)
        cv2.putText(status_view, "Attempts: " + str(getTotalAttempts(CURRENT_LEVEL)), (10,230), FONT, 0.8, COLOR_REGULAR, 1, cv2.LINE_AA)
        cv2.putText(status_view, formatDuration(getTotalDuration(CURRENT_LEVEL)), (10,260), FONT, 0.8, timerColor, 1, cv2.LINE_AA)

        cv2.putText(status_view, "------------- crop here ------------", (10,350), FONT, 0.4, (255,255,255), 1, cv2.LINE_AA)
        cv2.putText(status_view, ",".join(reversed(HISTORY)), (10,380), FONT, 0.4, (255,255,255), 1, cv2.LINE_AA)
        
        pausetext = "P: Pause" if not IS_PAUSED else "P: UnPause"
        cv2.putText(status_view, pausetext + ", S: Save, L: Set Level, N: Note/Milestone", (10,400), FONT, 0.4, (255,255,255), 1, cv2.LINE_AA)
        
        cv2.putText(status_view, "Q: Quit, G: CaptureRegion", (10,420), FONT, 0.4, (255,255,255), 1, cv2.LINE_AA)
        cv2.putText(status_view, "Last save: " + str(LAST_SAVE or "Never"), (10,440), FONT, 0.4, (255,255,255), 1, cv2.LINE_AA)

        cv2.imshow("Boris", status_view)


while True:
    PAUSE_STARTED = None
    PAUSED_DURATION = 0
    CURRENT_LEVEL = DATA["last_played"]
    if CURRENT_LEVEL is None:
        setLevel()

    RUNNING = True
    IS_PAUSED = False
    togglePause()

    SESSION["started"] = time.time()
    SESSION["durationAtStart"] = DATA["levels"][CURRENT_LEVEL]["duration"]
    runSessionLoop()