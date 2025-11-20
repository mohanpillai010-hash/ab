# abmain_fixed.py
"""
Modern single-page CustomTkinter UI for Mr. Pillai - Andar Bahar
- Non-blocking serial reader (works if shoe doesn't send newline)
- Scrollable single-page layout (title, joker, andar/bahar, controls, history)
- Image caching + safe loading (PIL -> CTkImage)
- Simple "pop" animation for win popup
- Keyboard shortcuts: '/' reset, '1' manual ANDAR, '2' manual BAHAR

This fixed version preserves the original UI and only applies minimal, targeted fixes:
- Adds missing game_label widget
- Ensures status_label exists (was added previously)
- Removes duplicate broken manual_result definition
- Adds evaluate_for_match(...) so serial-detected matches update counters
- Ensures thread-safe UI updates where serial thread calls tkinter
"""
import os
import time
import json
import threading
import serial
import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image, ImageTk

# ------------------ Configuration ------------------
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

# Try opening serial port (non-blocking)
SERIAL_PORT = "COM3"
BAUDRATE = 9600
try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0)  # non-blocking read
    print(f"✅ Connected to serial port {SERIAL_PORT}")
except Exception as e:
    print("⚠️ Serial not connected:", e)
    ser = None

# ------------------ State ------------------
joker_card = None
side_toggle = True       # True -> ANDAR, False -> BAHAR
game_over = False
winner_popup = None
BEAD_ROWS = 6
bead_columns = []
game_counter = 0
_image_cache = {}
stop_event = threading.Event()
andar_count = 0
bahar_count = 0

# ------------------ Helpers ------------------
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

# (keep this near your root initialization)
ctk.set_appearance_mode("dark")
root = ctk.CTk()
root.geometry("1200x700")
root.title("Mr. Pillai — Andar Bahar")

# --- Load the background image ---
# --- Transparent main content container ---
main_frame = ctk.CTkFrame(root, fg_color="transparent")
main_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1)

# safe background image path
bg_path = os.path.join(BASE_DIR, "a.jpg")
try:
    bg_img = ctk.CTkImage(Image.open(bg_path), size=(1080, 1920))
    bg_label = ctk.CTkLabel(main_frame, image=bg_img, text="")
    bg_label.place(relx=0.5, rely=0.5, anchor="center")
    bg_label.lift()  # push behind all other widgets in main_frame
except Exception:
    # if background missing, continue without it
    bg_label = None

# ------------------ TITLE ------------------
title = ctk.CTkLabel(
    main_frame,
    text="ANDAR (PILLAI) BAHAR ",
    font=ctk.CTkFont(size=95, weight="bold"),
    text_color="#E2DDFF"
)
title.pack(pady=(20, 15))

# Add game label (was missing in uploaded file)
game_label = ctk.CTkLabel(root,
                          text="Game: 0",
                          font=ctk.CTkFont(size=16, weight="bold"),
                          text_color="#ffd36e")
game_label.place(relx=0.5, rely=0.08, anchor="center")

status_label = ctk.CTkLabel(root,
                            text="Waiting...",
                            font=ctk.CTkFont(size=14),
                            text_color="#D6F2FF")
status_label.place(relx=0.5, rely=0.14, anchor="center")

# Counter display labels
andar_counter_label = ctk.CTkLabel(root,
                                   text="Andar Wins: 0",
                                   font=ctk.CTkFont(size=16, weight="bold"),
                                   text_color="#8ef0c6")
andar_counter_label.place(relx=0.25, rely=0.08, anchor="center")

bahar_counter_label = ctk.CTkLabel(root, text="Bahar Wins: 0",
                                   font=ctk.CTkFont(size=16, weight="bold"),
                                   text_color="#ff9c9c")
bahar_counter_label.place(relx=0.75, rely=0.08, anchor="center")

# ------------------ FLOATING CARDS AND CONTROLS ------------------

# ANDAR
andar_label = ctk.CTkLabel(root, text="ANDAR",
                           font=ctk.CTkFont(size=40, weight="bold"),
                           text_color="#8ef0c6")
andar_label.place(relx=0.25, rely=0.40, anchor="center")

andar_img_label = ctk.CTkLabel(root, text="", width=200, height=300,
                               fg_color="#B8C7FF", corner_radius=10)
andar_img_label.place(relx=0.25, rely=0.53, anchor="center")

# JOKER
joker_label = ctk.CTkLabel(root, text="JOKER",
                           font=ctk.CTkFont(size=50, weight="bold"),
                           text_color="#ffd36e")
joker_label.place(relx=0.5,  rely=0.40, anchor="center")

joker_img_label = ctk.CTkLabel(root, text="NEXT ROUND", width=220, height=320,
                               fg_color="#5C7FFF", corner_radius=10)
joker_img_label.place(relx=0.5,  rely=0.53, anchor="center")

joker_text = ctk.CTkLabel(root, text="",
                          font=ctk.CTkFont(size=14), text_color="#8fffd6")
joker_text.place(relx=0.5, rely=0.52, anchor="center")

# BAHAR
bahar_label = ctk.CTkLabel(root, text="BAHAR",
                           font=ctk.CTkFont(size=40, weight="bold"),
                           text_color="#ff9c9c")
bahar_label.place(relx=0.75, rely=0.40, anchor="center")

bahar_img_label = ctk.CTkLabel(root, text="", width=200, height=300,
                               fg_color="#B8C7FF", corner_radius=10)
bahar_img_label.place(relx=0.75, rely=0.53, anchor="center")

# Buttons a bit higher
ctk.CTkButton(root, text="New Round (/)", width=180,
              command=lambda: reset_game()).place(relx=0.36, rely=.9, anchor="center")
ctk.CTkButton(root, text="Manual Andar (1)", width=160,
              command=lambda: manual_result("ANDAR")).place(relx=0.5, rely=.9, anchor="center")
ctk.CTkButton(root, text="Manual Bahar (2)", width=160,
              command=lambda: manual_result("BAHAR")).place(relx=0.64, rely=.9, anchor="center")

#history
bead_canvas = ctk.CTkCanvas(root, height=160, bg="#1F51FF", highlightthickness=0)
bead_canvas.place(relx=0.5, rely=0.75, anchor="center", width=867)

# ------------------ Image loading / caching ------------------
def load_ctk_image(card_name, target_w=180, target_h=260):
    """Load a PNG from cards/ into a CTkImage (cached)."""
    if not card_name:
        return None
    key = f"{card_name}_{target_w}x{target_h}"
    if key in _image_cache:
        return _image_cache[key]
    img_path = os.path.join(CARDS_DIR, f"{card_name}.png")
    if not os.path.exists(img_path):
        _image_cache[key] = None
        return None
    try:
        pil_img = Image.open(img_path).convert("RGBA")
        ratio = pil_img.width / pil_img.height
        if ratio > (target_w / target_h):
            new_w = target_w
            new_h = int(target_w / ratio)
        else:
            new_h = target_h
            new_w = int(target_h * ratio)
        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
        ctk_img = CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
        _image_cache[key] = ctk_img
        return ctk_img
    except Exception as e:
        print("Image load error:", e)
        _image_cache[key] = None
        return None

def set_card_widget(widget, card_name):
    """Safely set a CTkLabel widget to show a card image or text fallback."""
    img = load_ctk_image(card_name)
    if img:
        widget.configure(image=img, text="")
        widget.image = img
    else:
        widget.configure(image=None, text=card_name or "(no image)")

# ------------------ Bead drawing ------------------
def draw_bead_plate():
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
                    fill = "#2bd6a6"; txt = "A"; txt_color = "#002218"
                else:
                    fill = "#ff6b6b"; txt = "B"; txt_color = "#3a0000"
                cx = x + cell_w // 2
                cy = y + cell_h // 2
                r = min(cell_w, cell_h) // 2 - 4
                bead_canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill=fill, outline="#001614")
                bead_canvas.create_text(cx, cy, text=txt, fill=txt_color, font=("Consolas", 20, "bold"))

def append_bead(symbol):
    if not bead_columns:
        bead_columns.append([])
    last = bead_columns[-1]
    if len(last) < BEAD_ROWS:
        last.append(symbol)
    else:
        bead_columns.append([symbol])
    draw_bead_plate()
    save_history_compact(symbol)

# ------------------ Game logic ------------------
def manual_result(side):
    global game_over, game_counter, andar_count, bahar_count
    if game_over:
        return
    game_over = True

    # update win counters
    if side == "ANDAR":
        andar_count += 1
        andar_counter_label.configure(text=f"Andar Wins: {andar_count}")
        append_bead("A")
    else:
        bahar_count += 1
        bahar_counter_label.configure(text=f"Bahar Wins: {bahar_count}")
        append_bead("B")

    # update total game counter
    game_counter += 1
    game_label.configure(text=f"Game: {game_counter}")

    show_popup(f"{side} WINS!")

def evaluate_for_match(card_name, side):
    global game_over, game_counter, andar_count, bahar_count
    if game_over or not joker_card:
        return

    if card_rank(card_name) == card_rank(joker_card):
        game_over = True
        symbol = "A" if side == "ANDAR" else "B"

        if side == "ANDAR":
            andar_count += 1
            andar_counter_label.configure(text=f"Andar Wins: {andar_count}")
        else:
            bahar_count += 1
            bahar_counter_label.configure(text=f"Bahar Wins: {bahar_count}")

        append_bead(symbol)

        game_counter += 1
        game_label.configure(text=f"Game: {game_counter}")

        show_popup(f"{side} WINS!")

def show_popup(text):
    global winner_popup
    # small animated popup
    try:
        if winner_popup and winner_popup.winfo_exists():
            winner_popup.destroy()
    except Exception:
        pass
    winner_popup = ctk.CTkToplevel(root)
    winner_popup.overrideredirect(True)
    winner_popup.configure(fg_color="#00271f", corner_radius=12)
    lbl = ctk.CTkLabel(winner_popup, text=text, font=ctk.CTkFont(size=22, weight="bold"), text_color="#ffd36e")
    lbl.pack(ipadx=20, ipady=16)
    # center
    x = root.winfo_screenwidth() // 2 - 150
    y = root.winfo_screenheight() // 2 - 60
    winner_popup.geometry(f"300x100+{x}+{y}")

    # simple pop scale animation: expand then shrink
    def close():
        try:
            if winner_popup and winner_popup.winfo_exists():
                winner_popup.destroy()
        except Exception:
            pass
    root.after(1400, close)

def log(msg: object) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    print(line.strip())

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
    joker_img_label.configure(text="", image=None)
    andar_img_label.configure(text="", image=None)
    bahar_img_label.configure(text="", image=None)

root.bind("/", lambda e: reset_game())
root.bind("1", lambda e: manual_result("ANDAR"))
root.bind("2", lambda e: manual_result("BAHAR"))

# ------------------ Serial reader (robust) ------------------
def serial_reader():
    global joker_card, side_toggle, game_over
    buffer = ""
    while not stop_event.is_set():
        if not ser:
            time.sleep(1)
            continue
        try:
            # read any available bytes; non-blocking
            n = ser.in_waiting or 1
            data = ser.read(n).decode(errors="ignore")
            if not data:
                time.sleep(0.02)
                continue
            buffer += data
            # Many shoe devices send 2-4 char tokens. We'll try to extract tokens from buffer.
            # Strategy: split by common separators if present, otherwise take 2-4 char chunks.
            # First handle if shoe sends separators like \r or \n:
            while '\\n' in buffer or '\\r' in buffer:
                # split on first newline-ish
                idx_n = min([i for i in (buffer.find('\\n'), buffer.find('\\r')) if i != -1])
                token = buffer[:idx_n].strip()
                buffer = buffer[idx_n+1:]
                if token:
                    process_token(token)
            # If no separators, try to take 2..4 char chunks while buffer length allows
            while len(buffer) >= 2:
                # many tokens are 2 (e.g. AH) or 3 (10S). We'll attempt 2..4 try-match approach.
                taken = False
                for L in (2, 3, 4):
                    if len(buffer) >= L:
                        candidate = buffer[:L].strip()
                        if candidate in card_map:
                            process_token(candidate)
                            buffer = buffer[L:]
                            taken = True
                            break
                if not taken:
                    # no match with fixed-length prefixes; if buffer is long, drop first char to resync
                    if len(buffer) > 8:
                        buffer = buffer[1:]
                    break
        except Exception as e:
            print("Serial Read Error:", e)
            time.sleep(0.1)
        time.sleep(0.01)

def process_token(raw_token):
    """Handle a token read from serial (mapped via card_map)."""
    global joker_card, side_toggle, game_over
    token = raw_token.strip()
    if not token:
        return
    print("[DEBUG] token:", repr(token))
    if token not in card_map:
        root.after(0, status_label.configure, {"text": f"Unknown raw token: {token}"})
        return
    card_name = card_map[token]
    root.after(0, status_label.configure, {"text": f"Card detected: {card_name}"})
    if not joker_card:
        joker_card = card_name
        root.after(0, joker_text.configure, {"text": f"Joker: {card_name}"})
        img = load_ctk_image(card_name, target_w=200, target_h=280)
        if img:
            root.after(0, lambda i=img: joker_img_label.configure(image=i, text="")); joker_img_label.image = img
        else:
            root.after(0, joker_img_label.configure, {"text": card_name})
        log(f"Joker set → {card_name}")
    else:
        side = "ANDAR" if side_toggle else "BAHAR"
        target_widget = andar_img_label if side_toggle else bahar_img_label
        img = load_ctk_image(card_name)
        if img:
            root.after(0, lambda w=target_widget, i=img: w.configure(image=i, text="")); target_widget.image = img
        else:
            root.after(0, target_widget.configure, {"text": card_name})
        # Use thread-safe call to evaluate_for_match
        root.after(0, evaluate_for_match, card_name, side)
        side_toggle = not side_toggle
        log(f"Card dealt → {card_name} ({side})")

# ------------------ Graceful exit ------------------
def on_close():
    stop_event.set()
    try:
        if ser and getattr(ser, "is_open", False):
            ser.close()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass

root.protocol("WM_DELETE_WINDOW", on_close)

# ------------------ Start serial thread, initial draw ------------------
draw_bead_plate()
threading.Thread(target=serial_reader, daemon=True).start()

root.mainloop()
