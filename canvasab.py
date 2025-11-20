import os
import time
import json
import threading
import serial
import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image

# ------------------ Configuration & Globals ------------------
# NOTE: You MUST have a valid 'cards' directory, 'a.jpg', and 'card_map.json'
# relative to where you run this script for it to work.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR = os.path.join(BASE_DIR, "cards")
CARD_MAP_PATH = os.path.join(BASE_DIR, "card_map.json")

# load card map
try:
    with open(CARD_MAP_PATH, "r", encoding="utf-8") as f:
        card_map = json.load(f)
except Exception as e:
    print("Failed to load card_map.json:", e)
    card_map = {}

# Try opening serial port (non-blocking) - CHANGE COM3 IF NEEDED
SERIAL_PORT = "COM3"
BAUDRATE = 9600
try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0)  # non-blocking read
    print(f"✅ Connected to serial port {SERIAL_PORT}")
except Exception as e:
    print("⚠️ Serial not connected:", e)
    ser = None

# ------------------ State Variables ------------------
joker_card = None
side_toggle = True  # True -> ANDAR, False -> BAHAR
game_over = False
winner_popup = None
BEAD_ROWS = 6
bead_columns = []
game_counter = 0
_image_cache = {}
stop_event = threading.Event()
andar_count = 0
bahar_count = 0


# ------------------ Helpers (for game logic) ------------------

def card_rank(card_name: str):
    """Normalize card rank (used for matching)."""
    if not card_name:
        return ""
    name = os.path.splitext(os.path.basename(card_name))[0].lower()
    if "_" in name:
        return name.split("_")[-1]
    else:
        return ''.join(ch for ch in name if ch.isalnum()).rstrip("shcd")


def save_history_compact(symbol):
    try:
        with open(os.path.join(BASE_DIR, "andar_history.txt"), "a", encoding="utf-8") as f:
            f.write(symbol + "\n")
    except Exception:
        pass


def load_ctk_image(card_name, target_w=180, target_h=260):
    """Load a PNG from cards/ into a CTkImage (cached)."""
    if not card_name: return None
    key = f"{card_name}_{target_w}x_{target_h}"
    if key in _image_cache: return _image_cache[key]
    img_path = os.path.join(CARDS_DIR, f"{card_name}.png")
    if not os.path.exists(img_path): return None
    try:
        pil_img = Image.open(img_path).convert("RGBA")
        # Resize logic to fit card dimensions
        ratio = pil_img.width / pil_img.height
        new_w = target_w;
        new_h = target_h
        if ratio > (target_w / target_h):
            new_h = int(target_w / ratio)
        else:
            new_w = int(target_h * ratio)
        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
        ctk_img = CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
        _image_cache[key] = ctk_img
        return ctk_img
    except Exception as e:
        print("Image load error:", e)
        return None


def set_card_widget(widget, card_name):
    """Safely set a CTkLabel widget to show a card image or text fallback."""
    img = load_ctk_image(card_name)
    if img:
        widget.configure(image=img, text="")
        widget.image = img
    else:
        widget.configure(image=None, text=card_name or "(no image)")


# ------------------ UI Setup (Canvas Method) ------------------

# Screen dimensions for absolute positioning
SCREEN_W = 1080
SCREEN_H = 1920

ctk.set_appearance_mode("system")
root = ctk.CTk()
root.geometry(f"{SCREEN_W}x{SCREEN_H}")
root.title("Mr. Pillai — Andar Bahar")
import os
import time
import json
import threading
import serial
import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image

# ------------------ Configuration & Globals ------------------
# NOTE: You MUST have a valid 'cards' directory, 'a.jpg', and 'card_map.json'
# relative to where you run this script for it to work.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR = os.path.join(BASE_DIR, "cards")
CARD_MAP_PATH = os.path.join(BASE_DIR, "card_map.json")

# load card map
try:
    with open(CARD_MAP_PATH, "r", encoding="utf-8") as f:
        card_map = json.load(f)
except Exception as e:
    print("Failed to load card_map.json:", e)
    card_map = {}

# Try opening serial port (non-blocking) - CHANGE COM3 IF NEEDED
SERIAL_PORT = "COM3"
BAUDRATE = 9600
try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0)  # non-blocking read
    print(f"✅ Connected to serial port {SERIAL_PORT}")
except Exception as e:
    print("⚠️ Serial not connected:", e)
    ser = None

# ------------------ State Variables ------------------
joker_card = None
side_toggle = True  # True -> ANDAR, False -> BAHAR
game_over = False
winner_popup = None
BEAD_ROWS = 6
bead_columns = []
game_counter = 0
_image_cache = {}
stop_event = threading.Event()
andar_count = 0
bahar_count = 0


# ------------------ Helpers (for game logic) ------------------

def card_rank(card_name: str):
    """Normalize card rank (used for matching)."""
    if not card_name:
        return ""
    name = os.path.splitext(os.path.basename(card_name))[0].lower()
    if "_" in name:
        return name.split("_")[-1]
    else:
        return ''.join(ch for ch in name if ch.isalnum()).rstrip("shcd")


def save_history_compact(symbol):
    try:
        with open(os.path.join(BASE_DIR, "andar_history.txt"), "a", encoding="utf-8") as f:
            f.write(symbol + "\n")
    except Exception:
        pass


def load_ctk_image(card_name, target_w=180, target_h=260):
    """Load a PNG from cards/ into a CTkImage (cached)."""
    if not card_name: return None
    key = f"{card_name}_{target_w}x_{target_h}"
    if key in _image_cache: return _image_cache[key]
    img_path = os.path.join(CARDS_DIR, f"{card_name}.png")
    if not os.path.exists(img_path): return None
    try:
        pil_img = Image.open(img_path).convert("RGBA")
        # Resize logic to fit card dimensions
        ratio = pil_img.width / pil_img.height
        new_w = target_w;
        new_h = target_h
        if ratio > (target_w / target_h):
            new_h = int(target_w / ratio)
        else:
            new_w = int(target_h * ratio)
        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
        ctk_img = CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
        _image_cache[key] = ctk_img
        return ctk_img
    except Exception as e:
        print("Image load error:", e)
        return None


def set_card_widget(widget, card_name):
    """Safely set a CTkLabel widget to show a card image or text fallback."""
    img = load_ctk_image(card_name)
    if img:
        widget.configure(image=img, text="")
        widget.image = img
    else:
        widget.configure(image=None, text=card_name or "(no image)")


# ------------------ UI Setup (Canvas Method) ------------------

# Screen dimensions for absolute positioning
SCREEN_W = 1080
SCREEN_H = 1920

ctk.set_appearance_mode("system")
root = ctk.CTk()
root.geometry(f"{SCREEN_W}x{SCREEN_H}")
root.title("Mr. Pillai — Andar Bahar")

# 1. Create the main CTkCanvas on root
# This will hold the background image and all other widgets
main_canvas = ctk.CTkCanvas(root,
                            width=SCREEN_W,
                            height=SCREEN_H,
                            highlightthickness=0,
                            # FIX 1: Use a safe hex color instead of internal CustomTkinter lookup
                            bg="#000000")
main_canvas.pack(fill="both", expand=True)

# 2. Load and place the background image onto the Canvas
bg_label = None  # We'll use this for the layering logic
bg_img_ref = None  # Holds the reference for the canvas item

try:
    # Load the background image
    bg_path = os.path.join(BASE_DIR, "a.jpg")
    bg_img = Image.open(bg_path).resize((SCREEN_W, SCREEN_H), Image.LANCZOS)
    bg_tk_img = ctk.CTkImage(light_image=bg_img, dark_image=bg_img, size=(SCREEN_W, SCREEN_H))

    # Place the image in the center of the canvas
    bg_img_ref = main_canvas.create_image(
        SCREEN_W // 2,
        SCREEN_H // 2,
        image=bg_tk_img,
        anchor="center"
    )
    # Store the reference to keep it from being garbage collected
    main_canvas.bg_tk_img = bg_tk_img

except Exception as e:
    print(f"⚠️ Failed to load background image 'a.jpg': {e}")


# ------------------ WIDGET DEFINITIONS (Parented to root, Placed via Canvas) ------------------

# Helper function to convert rel coordinates to absolute
def abs_coords(relx, rely):
    return int(SCREEN_W * relx), int(SCREEN_H * rely)


# --- TITLE ---
title = ctk.CTkLabel(
    root,  # Parent is root
    text="ANDAR        BAHAR ",
    font=ctk.CTkFont(size=95, weight="bold"),
    text_color="#E2DDFF",
    fg_color="transparent"
)
x, y = abs_coords(0.5, 0.04)
main_canvas.create_window(x, y, window=title, anchor="center")

# --- Status Label (CASINO GOLD) ---
status_label = ctk.CTkLabel(root,
                            text="CASINO GOLD",
                            font=ctk.CTkFont(size=100),
                            text_color="#D6F2FF",
                            fg_color="transparent")
x, y = abs_coords(0.5, 0.14)
main_canvas.create_window(x, y, window=status_label, anchor="center")

# --- Game Counter ---
game_label = ctk.CTkLabel(root,
                          text="0",
                          font=ctk.CTkFont(size=70, weight="bold"),
                          text_color="#ffd36e",
                          fg_color="transparent")
x, y = abs_coords(0.5, 0.30)
main_canvas.create_window(x, y, window=game_label, anchor="center")

# --- Andar Counter ---
andar_counter_label = ctk.CTkLabel(root,
                                   text="0",
                                   font=ctk.CTkFont(size=80, weight="bold"),
                                   text_color="#8ef0c6",
                                   fg_color="transparent")
x, y = abs_coords(0.25, 0.35)
main_canvas.create_window(x, y, window=andar_counter_label, anchor="center")

# --- Bahar Counter ---
bahar_counter_label = ctk.CTkLabel(root, text="0",
                                   font=ctk.CTkFont(size=80, weight="bold"),
                                   text_color="#ff9c9c",
                                   fg_color="transparent")
x, y = abs_coords(0.75, 0.35)
main_canvas.create_window(x, y, window=bahar_counter_label, anchor="center")

# ------------------ FLOATING CARDS ------------------

# --- ANDAR Text ---
andar_label = ctk.CTkLabel(root, text="ANDAR",
                           font=ctk.CTkFont(size=40, weight="bold"),
                           text_color="#8ef0c6",
                           fg_color="transparent")
x, y = abs_coords(0.25, 0.40)
main_canvas.create_window(x, y, window=andar_label, anchor="center")

# --- Andar Card Image Label ---
andar_img_label = ctk.CTkLabel(root, text="", width=200, height=300,
                               fg_color="transparent",
                               corner_radius=10)
x, y = abs_coords(0.25, 0.53)
main_canvas.create_window(x, y, window=andar_img_label, anchor="center")

# --- JOKER Text ---
joker_label = ctk.CTkLabel(root, text="JOKER",
                           font=ctk.CTkFont(size=50, weight="bold"),
                           text_color="#ffd36e",
                           fg_color="transparent")
x, y = abs_coords(0.5, 0.40)
main_canvas.create_window(x, y, window=joker_label, anchor="center")

# --- Joker Card Image Label ---
joker_img_label = ctk.CTkLabel(root, text="NEXT ROUND", width=220, height=320,
                               fg_color="transparent",
                               corner_radius=10)
x, y = abs_coords(0.5, 0.53)
main_canvas.create_window(x, y, window=joker_img_label, anchor="center")

joker_text = ctk.CTkLabel(root, text="",
                          font=ctk.CTkFont(size=14), text_color="#8fffd6",
                          fg_color="transparent")
x, y = abs_coords(0.5, 0.52)
# NOTE: Positioning slightly offset from center of card for visual effect
main_canvas.create_window(x, y - 10, window=joker_text, anchor="center")

# --- BAHAR Text ---
bahar_label = ctk.CTkLabel(root, text="BAHAR",
                           font=ctk.CTkFont(size=40, weight="bold"),
                           text_color="#ff9c9c",
                           fg_color="transparent")
x, y = abs_coords(0.75, 0.40)
main_canvas.create_window(x, y, window=bahar_label, anchor="center")

# --- Bahar Card Image Label ---
bahar_img_label = ctk.CTkLabel(root, text="", width=200, height=300,
                               fg_color="transparent",
                               corner_radius=10)
x, y = abs_coords(0.75, 0.53)
main_canvas.create_window(x, y, window=bahar_img_label, anchor="center")

# --- History Canvas (Nested) ---
# NOTE: This is a nested canvas placed inside the main canvas via create_window
bead_canvas = ctk.CTkCanvas(root, height=160,
                            highlightthickness=0,
                            bg="#000000",
                            highlightbackground="#000000"
                            )
x, y = abs_coords(0.5, 0.75)
main_canvas.create_window(x, y, window=bead_canvas, anchor="center", width=1200)

# --- Buttons ---
x1, y1 = abs_coords(0.36, 0.9)
x2, y2 = abs_coords(0.5, 0.9)
x3, y3 = abs_coords(0.64, 0.9)

btn1 = ctk.CTkButton(root, text="New Round (/)", width=180, command=lambda: reset_game())
btn2 = ctk.CTkButton(root, text="Manual Andar (1)", width=160, command=lambda: manual_result("ANDAR"))
btn3 = ctk.CTkButton(root, text="Manual Bahar (2)", width=160, command=lambda: manual_result("BAHAR"))

# FIX 2: Place buttons using the main_canvas.create_window for correct layering and positioning
main_canvas.create_window(x1, y1, window=btn1, anchor="center")
main_canvas.create_window(x2, y2, window=btn2, anchor="center")
main_canvas.create_window(x3, y3, window=btn3, anchor="center")


# ------------------ Game/Serial Logic (continued) ------------------

def draw_bead_plate():
    # Uses the nested bead_canvas
    try:
        bead_canvas.delete("all")
    except Exception:
        pass
    cols = max(1, len(bead_columns))
    cell_w = 34
    cell_h = 34
    pad_x = 8
    pad_y = 12
    width = cols * (cell_w + 8) + pad_x * 2
    height = BEAD_ROWS * (cell_h + 6) + pad_y * 2
    try:
        bead_canvas.configure(width=min(width, 1200), height=height)
    except Exception:
        pass
    for ci, col in enumerate(bead_columns):
        for ri in range(BEAD_ROWS):
            x = pad_x + ci * (cell_w + 8)
            y = pad_y + ri * (cell_h + 6)
            bead_canvas.create_rectangle(x, y, x + cell_w, y + cell_h, fill="#02221b", outline="#00160f")
            if ri < len(col):
                val = col[ri]
                if val == "A":
                    fill = "#2bd6a6";
                    txt = "A";
                    txt_color = "#002218"
                else:
                    fill = "#ff6b6b";
                    txt = "B";
                    txt_color = "#3a0000"
                cx = x + cell_w // 2
                cy = y + cell_h // 2
                r = min(cell_w, cell_h) // 2 - 4
                bead_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline="#001614")
                bead_canvas.create_text(cx, cy, text=txt, fill=txt_color, font=("Consolas", 20, "bold"))


def append_bead(symbol):
    if not bead_columns: bead_columns.append([])
    last = bead_columns[-1]
    if len(last) < BEAD_ROWS:
        last.append(symbol)
    else:
        bead_columns.append([symbol])
    draw_bead_plate()
    save_history_compact(symbol)


def show_popup(text):
    global winner_popup
    try:
        if winner_popup and winner_popup.winfo_exists(): winner_popup.destroy()
    except Exception:
        pass
    winner_popup = ctk.CTkToplevel(root)
    winner_popup.overrideredirect(True)
    winner_popup.configure(fg_color="#00271f", corner_radius=12)
    lbl = ctk.CTkLabel(winner_popup, text=text, font=ctk.CTkFont(size=22, weight="bold"), text_color="#ffd36e")
    lbl.pack(ipadx=20, ipady=16)
    x = root.winfo_screenwidth() // 2 - 150
    y = root.winfo_screenheight() // 2 - 60
    winner_popup.geometry(f"300x100+{x}+{y}")
    root.after(1400, lambda: winner_popup.destroy() if winner_popup and winner_popup.winfo_exists() else None)


def manual_result(side):
    global game_over, game_counter, andar_count, bahar_count
    if game_over: return
    game_over = True
    if side == "ANDAR":
        andar_count += 1
        andar_counter_label.configure(text=f"{andar_count}")
        append_bead("A")
    else:
        bahar_count += 1
        bahar_counter_label.configure(text=f"{bahar_count}")
        append_bead("B")
    game_counter += 1
    game_label.configure(text=f"{game_counter}")
    show_popup(f"{side} WINS!")


def evaluate_for_match(card_name, side):
    global game_over, game_counter, andar_count, bahar_count
    if game_over or not joker_card: return

    if card_rank(card_name) == card_rank(joker_card):
        game_over = True
        symbol = "A" if side == "ANDAR" else "B"
        if side == "ANDAR":
            andar_count += 1
        else:
            bahar_count += 1
        andar_counter_label.configure(text=f"{andar_count}")
        bahar_counter_label.configure(text=f"{bahar_count}")
        append_bead(symbol)
        game_counter += 1
        game_label.configure(text=f"{game_counter}")
        show_popup(f"{side} WINS!")


def reset_game(event=None):
    global joker_card, side_toggle, game_over, winner_popup
    if winner_popup and winner_popup.winfo_exists():
        try:
            winner_popup.destroy()
        except Exception:
            pass
    joker_card = None
    side_toggle = True
    game_over = False
    joker_text.configure(text="")
    joker_img_label.configure(text="NEXT ROUND", image=None)
    andar_img_label.configure(text="", image=None)
    bahar_img_label.configure(text="", image=None)


root.bind("/", lambda e: reset_game())
root.bind("1", lambda e: manual_result("ANDAR"))
root.bind("2", lambda e: manual_result("BAHAR"))


# ------------------ Serial Logic ------------------

def process_token(raw_token):
    """Handle a token read from serial (mapped via card_map)."""
    global joker_card, side_toggle, game_over
    token = raw_token.strip()
    if not token or token not in card_map:
        root.after(0, status_label.configure, {"text": f"Unknown raw token: {token}"})
        return

    card_name = card_map[token]
    root.after(0, status_label.configure, {"text": f"Card detected: {card_name}"})

    if not joker_card:
        joker_card = card_name
        root.after(0, joker_text.configure, {"text": f"Joker: {card_name}"})
        img = load_ctk_image(card_name, target_w=200, target_h=280)

        def update_joker(w, i):
            w.configure(image=i, text=""); w.image = i

        root.after(0, update_joker, joker_img_label, img)

    else:
        side = "ANDAR" if side_toggle else "BAHAR"
        target_widget = andar_img_label if side_toggle else bahar_img_label
        img = load_ctk_image(card_name)

        def update_card(w, i):
            w.configure(image=i, text=""); w.image = i

        root.after(0, update_card, target_widget, img)

        root.after(0, evaluate_for_match, card_name, side)
        side_toggle = not side_toggle


def serial_reader():
    if not ser: time.sleep(1); return
    buffer = ""
    while not stop_event.is_set():
        try:
            n = ser.in_waiting or 1
            data = ser.read(n).decode(errors="ignore")
            if not data: time.sleep(0.02); continue
            buffer += data
            # Simplified token processing loop
            while '\n' in buffer or '\r' in buffer:
                idx_n = min([i for i in (buffer.find('\n'), buffer.find('\r')) if i != -1])
                token = buffer[:idx_n].strip()
                buffer = buffer[idx_n + 1:]
                if token: process_token(token)
            # Fallback for short tokens
            while len(buffer) >= 2:
                taken = False
                for L in (2, 3, 4):
                    if len(buffer) >= L:
                        candidate = buffer[:L].strip()
                        if candidate in card_map:
                            process_token(candidate)
                            buffer = buffer[L:]
                            taken = True
                            break
                if not taken: break
        except Exception:
            time.sleep(0.1)
        time.sleep(0.01)


# ------------------ Start / Cleanup ------------------

def on_close():
    stop_event.set()
    try:
        if ser and getattr(ser, "is_open", False): ser.close()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass


root.protocol("WM_DELETE_WINDOW", on_close)

draw_bead_plate()
threading.Thread(target=serial_reader, daemon=True).start()

root.mainloop()/
# 1. Create the main CTkCanvas on root
# This will hold the background image and all other widgets
main_canvas = ctk.CTkCanvas(root,
                            width=SCREEN_W,
                            height=SCREEN_H,
                            highlightthickness=0,
                            bg=root._fg_color[root._appearance_mode])
main_canvas.pack(fill="both", expand=True)

# 2. Load and place the background image onto the Canvas
bg_label = None  # We'll use this for the layering logic
bg_img_ref = None  # Holds the reference for the canvas item

try:
    # Load the background image
    bg_path = os.path.join(BASE_DIR, "a.jpg")
    bg_img = Image.open(bg_path).resize((SCREEN_W, SCREEN_H), Image.LANCZOS)
    bg_tk_img = ctk.CTkImage(light_image=bg_img, dark_image=bg_img, size=(SCREEN_W, SCREEN_H))

    # Place the image in the center of the canvas
    bg_img_ref = main_canvas.create_image(
        SCREEN_W // 2,
        SCREEN_H // 2,
        image=bg_tk_img,
        anchor="center"
    )
    # Store the reference to keep it from being garbage collected
    main_canvas.bg_tk_img = bg_tk_img

except Exception as e:
    print(f"⚠️ Failed to load background image 'a.jpg': {e}")


# ------------------ WIDGET DEFINITIONS (Parented to root, Placed via Canvas) ------------------

# Helper function to convert rel coordinates to absolute
def abs_coords(relx, rely):
    return int(SCREEN_W * relx), int(SCREEN_H * rely)


# --- TITLE ---
title = ctk.CTkLabel(
    root,  # Parent is root
    text="ANDAR        BAHAR ",
    font=ctk.CTkFont(size=95, weight="bold"),
    text_color="#E2DDFF",
    fg_color="transparent"
)
x, y = abs_coords(0.5, 0.04)
main_canvas.create_window(x, y, window=title, anchor="center")

# --- Status Label (CASINO GOLD) ---
status_label = ctk.CTkLabel(root,
                            text="CASINO GOLD",
                            font=ctk.CTkFont(size=100),
                            text_color="#D6F2FF",
                            fg_color="transparent")
x, y = abs_coords(0.5, 0.14)
main_canvas.create_window(x, y, window=status_label, anchor="center")

# --- Game Counter ---
game_label = ctk.CTkLabel(root,
                          text="0",
                          font=ctk.CTkFont(size=70, weight="bold"),
                          text_color="#ffd36e",
                          fg_color="transparent")
x, y = abs_coords(0.5, 0.30)
main_canvas.create_window(x, y, window=game_label, anchor="center")

# --- Andar Counter ---
andar_counter_label = ctk.CTkLabel(root,
                                   text="0",
                                   font=ctk.CTkFont(size=80, weight="bold"),
                                   text_color="#8ef0c6",
                                   fg_color="transparent")
x, y = abs_coords(0.25, 0.35)
main_canvas.create_window(x, y, window=andar_counter_label, anchor="center")

# --- Bahar Counter ---
bahar_counter_label = ctk.CTkLabel(root, text="0",
                                   font=ctk.CTkFont(size=80, weight="bold"),
                                   text_color="#ff9c9c",
                                   fg_color="transparent")
x, y = abs_coords(0.75, 0.35)
main_canvas.create_window(x, y, window=bahar_counter_label, anchor="center")

# ------------------ FLOATING CARDS ------------------

# --- ANDAR Text ---
andar_label = ctk.CTkLabel(root, text="ANDAR",
                           font=ctk.CTkFont(size=40, weight="bold"),
                           text_color="#8ef0c6",
                           fg_color="transparent")
x, y = abs_coords(0.25, 0.40)
main_canvas.create_window(x, y, window=andar_label, anchor="center")

# --- Andar Card Image Label ---
andar_img_label = ctk.CTkLabel(root, text="", width=200, height=300,
                               fg_color="transparent",
                               corner_radius=10)
x, y = abs_coords(0.25, 0.53)
main_canvas.create_window(x, y, window=andar_img_label, anchor="center")

# --- JOKER Text ---
joker_label = ctk.CTkLabel(root, text="JOKER",
                           font=ctk.CTkFont(size=50, weight="bold"),
                           text_color="#ffd36e",
                           fg_color="transparent")
x, y = abs_coords(0.5, 0.40)
main_canvas.create_window(x, y, window=joker_label, anchor="center")

# --- Joker Card Image Label ---
joker_img_label = ctk.CTkLabel(root, text="NEXT ROUND", width=220, height=320,
                               fg_color="transparent",
                               corner_radius=10)
x, y = abs_coords(0.5, 0.53)
main_canvas.create_window(x, y, window=joker_img_label, anchor="center")

joker_text = ctk.CTkLabel(root, text="",
                          font=ctk.CTkFont(size=14), text_color="#8fffd6",
                          fg_color="transparent")
x, y = abs_coords(0.5, 0.52)
# NOTE: Positioning slightly offset from center of card for visual effect
main_canvas.create_window(x, y - 10, window=joker_text, anchor="center")

# --- BAHAR Text ---
bahar_label = ctk.CTkLabel(root, text="BAHAR",
                           font=ctk.CTkFont(size=40, weight="bold"),
                           text_color="#ff9c9c",
                           fg_color="transparent")
x, y = abs_coords(0.75, 0.40)
main_canvas.create_window(x, y, window=bahar_label, anchor="center")

# --- Bahar Card Image Label ---
bahar_img_label = ctk.CTkLabel(root, text="", width=200, height=300,
                               fg_color="transparent",
                               corner_radius=10)
x, y = abs_coords(0.75, 0.53)
main_canvas.create_window(x, y, window=bahar_img_label, anchor="center")

# --- History Canvas (Nested) ---
# NOTE: This is a nested canvas placed inside the main canvas via create_window
bead_canvas = ctk.CTkCanvas(root, height=160,
                            highlightthickness=0,
                            bg="#000000",
                            highlightbackground="#000000"
                            )
x, y = abs_coords(0.5, 0.75)
main_canvas.create_window(x, y, window=bead_canvas, anchor="center", width=1200)

# --- Buttons ---
x1, y1 = abs_coords(0.36, 0.9)
x2, y2 = abs_coords(0.5, 0.9)
x3, y3 = abs_coords(0.64, 0.9)

ctk.CTkButton(root, text="New Round (/)", width=180,
              command=lambda: reset_game()).place(x=x1, y=y1, anchor="center")
ctk.CTkButton(root, text="Manual Andar (1)", width=160,
              command=lambda: manual_result("ANDAR")).place(x=x2, y=y2, anchor="center")
ctk.CTkButton(root, text="Manual Bahar (2)", width=160,
              command=lambda: manual_result("BAHAR")).place(x=x3, y=y3, anchor="center")


# ------------------ Game/Serial Logic (continued) ------------------

def draw_bead_plate():
    # Uses the nested bead_canvas
    # This logic remains the same as it draws on the internal canvas
    try:
        bead_canvas.delete("all")
    except Exception:
        pass
    # ... (Bead drawing implementation) ... (Too long to include here, assuming it works)
    cols = max(1, len(bead_columns))
    cell_w = 34
    cell_h = 34
    pad_x = 8
    pad_y = 12
    width = cols * (cell_w + 8) + pad_x * 2
    height = BEAD_ROWS * (cell_h + 6) + pad_y * 2
    try:
        bead_canvas.configure(width=min(width, 1200), height=height)
    except Exception:
        pass
    for ci, col in enumerate(bead_columns):
        for ri in range(BEAD_ROWS):
            x = pad_x + ci * (cell_w + 8)
            y = pad_y + ri * (cell_h + 6)
            bead_canvas.create_rectangle(x, y, x + cell_w, y + cell_h, fill="#02221b", outline="#00160f")
            if ri < len(col):
                val = col[ri]
                if val == "A":
                    fill = "#2bd6a6";
                    txt = "A";
                    txt_color = "#002218"
                else:
                    fill = "#ff6b6b";
                    txt = "B";
                    txt_color = "#3a0000"
                cx = x + cell_w // 2
                cy = y + cell_h // 2
                r = min(cell_w, cell_h) // 2 - 4
                bead_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline="#001614")
                bead_canvas.create_text(cx, cy, text=txt, fill=txt_color, font=("Consolas", 20, "bold"))


def append_bead(symbol):
    if not bead_columns: bead_columns.append([])
    last = bead_columns[-1]
    if len(last) < BEAD_ROWS:
        last.append(symbol)
    else:
        bead_columns.append([symbol])
    draw_bead_plate()
    save_history_compact(symbol)


def show_popup(text):
    global winner_popup
    try:
        if winner_popup and winner_popup.winfo_exists(): winner_popup.destroy()
    except Exception:
        pass
    winner_popup = ctk.CTkToplevel(root)
    winner_popup.overrideredirect(True)
    winner_popup.configure(fg_color="#00271f", corner_radius=12)
    lbl = ctk.CTkLabel(winner_popup, text=text, font=ctk.CTkFont(size=22, weight="bold"), text_color="#ffd36e")
    lbl.pack(ipadx=20, ipady=16)
    x = root.winfo_screenwidth() // 2 - 150
    y = root.winfo_screenheight() // 2 - 60
    winner_popup.geometry(f"300x100+{x}+{y}")
    root.after(1400, lambda: winner_popup.destroy() if winner_popup and winner_popup.winfo_exists() else None)


def manual_result(side):
    global game_over, game_counter, andar_count, bahar_count
    if game_over: return
    game_over = True
    if side == "ANDAR":
        andar_count += 1
        andar_counter_label.configure(text=f"{andar_count}")
        append_bead("A")
    else:
        bahar_count += 1
        bahar_counter_label.configure(text=f"{bahar_count}")
        append_bead("B")
    game_counter += 1
    game_label.configure(text=f"{game_counter}")
    show_popup(f"{side} WINS!")


def evaluate_for_match(card_name, side):
    global game_over, game_counter, andar_count, bahar_count
    if game_over or not joker_card: return

    if card_rank(card_name) == card_rank(joker_card):
        game_over = True
        symbol = "A" if side == "ANDAR" else "B"
        if side == "ANDAR":
            andar_count += 1
        else:
            bahar_count += 1
        andar_counter_label.configure(text=f"{andar_count}")
        bahar_counter_label.configure(text=f"{bahar_count}")
        append_bead(symbol)
        game_counter += 1
        game_label.configure(text=f"{game_counter}")
        show_popup(f"{side} WINS!")


def reset_game(event=None):
    global joker_card, side_toggle, game_over, winner_popup
    if winner_popup and winner_popup.winfo_exists():
        try:
            winner_popup.destroy()
        except Exception:
            pass
    joker_card = None
    side_toggle = True
    game_over = False
    joker_text.configure(text="")
    joker_img_label.configure(text="NEXT ROUND", image=None)
    andar_img_label.configure(text="", image=None)
    bahar_img_label.configure(text="", image=None)


root.bind("/", lambda e: reset_game())
root.bind("1", lambda e: manual_result("ANDAR"))
root.bind("2", lambda e: manual_result("BAHAR"))


# ------------------ Serial Logic ------------------

def process_token(raw_token):
    """Handle a token read from serial (mapped via card_map)."""
    global joker_card, side_toggle, game_over
    token = raw_token.strip()
    if not token or token not in card_map:
        root.after(0, status_label.configure, {"text": f"Unknown raw token: {token}"})
        return

    card_name = card_map[token]
    root.after(0, status_label.configure, {"text": f"Card detected: {card_name}"})

    if not joker_card:
        joker_card = card_name
        root.after(0, joker_text.configure, {"text": f"Joker: {card_name}"})
        img = load_ctk_image(card_name, target_w=200, target_h=280)

        def update_joker(w, i):
            w.configure(image=i, text=""); w.image = i

        root.after(0, update_joker, joker_img_label, img)

    else:
        side = "ANDAR" if side_toggle else "BAHAR"
        target_widget = andar_img_label if side_toggle else bahar_img_label
        img = load_ctk_image(card_name)

        def update_card(w, i):
            w.configure(image=i, text=""); w.image = i

        root.after(0, update_card, target_widget, img)

        root.after(0, evaluate_for_match, card_name, side)
        side_toggle = not side_toggle


def serial_reader():
    if not ser: time.sleep(1); return
    buffer = ""
    while not stop_event.is_set():
        try:
            n = ser.in_waiting or 1
            data = ser.read(n).decode(errors="ignore")
            if not data: time.sleep(0.02); continue
            buffer += data
            # Simplified token processing loop
            while '\n' in buffer or '\r' in buffer:
                idx_n = min([i for i in (buffer.find('\n'), buffer.find('\r')) if i != -1])
                token = buffer[:idx_n].strip()
                buffer = buffer[idx_n + 1:]
                if token: process_token(token)
            # Fallback for short tokens
            while len(buffer) >= 2:
                taken = False
                for L in (2, 3, 4):
                    if len(buffer) >= L:
                        candidate = buffer[:L].strip()
                        if candidate in card_map:
                            process_token(candidate)
                            buffer = buffer[L:]
                            taken = True
                            break
                if not taken: break
        except Exception:
            time.sleep(0.1)
        time.sleep(0.01)


# ------------------ Start / Cleanup ------------------

def on_close():
    stop_event.set()
    try:
        if ser and getattr(ser, "is_open", False): ser.close()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass


root.protocol("WM_DELETE_WINDOW", on_close)

draw_bead_plate()
threading.Thread(target=serial_reader, daemon=True).start()

root.mainloop()