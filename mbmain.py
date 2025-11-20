# mb_casino_bead.py
import customtkinter as ctk
from customtkinter import CTkImage
import threading, serial, json, os, time
from PIL import Image

# ------------------ Setup ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR = os.path.join(BASE_DIR, "cards")

with open(os.path.join(BASE_DIR, "card_map.json"), "r", encoding="utf-8") as f:
    card_map = json.load(f)

# Serial connection
try:
    ser = serial.Serial("COM3", 9600, timeout=1)
    print("✅ Connected to serial port COM3")
except Exception as e:
    print("⚠️ Serial not connected:", e)
    ser = None

# CTk setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

root = ctk.CTk()
root.title("🎴 Mr. Pillai — Baccarat (Bead Grid UI)")
try:
    root.state("zoomed")
except Exception:
    pass
root.configure(fg_color="#071a13")

# ------------------ State ------------------
deal_cards, player_cards, banker_cards = [], [], []
game_over = False
winner_popup = None

# derived counters
counters = {
    "PLAYER": 0,
    "BANKER": 0,
    "TIE": 0,
    "PLAYER_PAIR": 0,
    "BANKER_PAIR": 0,
    "NATURAL": 0,
    "SUPER_SIX": 0
}

# bead (bead-style scoreboard) storage
BEAD_ROWS = 6
bead_columns = []  # list of lists; each inner list is up to BEAD_ROWS symbols ('P','B','T')

# Keep a global image cache so images are not garbage-collected
_image_cache = {}

# Thread stop event for graceful exit
stop_event = threading.Event()

# ------------------ Helpers ------------------
def card_rank(card_name: str):
    name = os.path.splitext(os.path.basename(card_name))[0].lower()
    if "_" in name:
        rank = name.split("_")[-1]
    else:
        rank = ''.join(ch for ch in name if ch.isalnum()).rstrip("shcd")
    return rank

def card_point(card_name: str):
    rank = card_rank(card_name)
    if rank in ("10", "jack", "queen", "king", "j", "q", "k"):
        return 0
    if rank in ("ace", "a"):
        return 1
    try:
        return int(rank)
    except Exception:
        return 0

def compute_total(cards):
    return sum(card_point(c) for c in cards) % 10

def save_history_compact(symbol):
    """Append compact symbol (P/B/T) into a simple text file (utf-8)."""
    try:
        with open(os.path.join(BASE_DIR, "baccarat_history.txt"), "a", encoding="utf-8") as f:
            f.write(symbol)
            f.write("\n")
    except Exception as e:
        print("History write error:", e)

# ------------------ Layout ------------------
# Top header
top = ctk.CTkFrame(root, fg_color="#07281f", corner_radius=12)
top.pack(fill="x", padx=20, pady=(16,8))
title = ctk.CTkLabel(top, text="BACCARAT", font=("Arial Black", 36), text_color="#bce0c6")
title.grid(row=0, column=0, sticky="w", padx=14, pady=10)
game_num_label = ctk.CTkLabel(top, text="Game: 0", font=("Arial", 16), text_color="#ffd36e")
game_num_label.grid(row=0, column=1, sticky="e", padx=14)

# main board frame
board = ctk.CTkFrame(root, fg_color="#052a22", corner_radius=14)
board.pack(fill="x", padx=20, pady=8)

# Player column
player_col = ctk.CTkFrame(board, fg_color="#042f2a", corner_radius=10)
player_col.grid(row=0, column=0, padx=18, pady=12, sticky="n")
player_label = ctk.CTkLabel(player_col, text="PLAYER", font=("Arial Black", 18), text_color="#8ef0c6")
player_label.pack(padx=10, pady=(10,6))
p_cards_frame = ctk.CTkFrame(player_col, fg_color="#021a17", corner_radius=8)
p_cards_frame.pack(padx=8, pady=6)
p_card_labels = [ctk.CTkLabel(p_cards_frame, text="", width=110, height=150, corner_radius=8, fg_color="#021a17") for _ in range(3)]
for lbl in p_card_labels:
    lbl.pack(side="left", padx=6, pady=10)
player_score = ctk.CTkLabel(player_col, text="Score: -", font=("Arial", 14))
player_score.pack(pady=6)

# center column (counters + bead scoreboard)
center_col = ctk.CTkFrame(board, fg_color="#041f1c", corner_radius=8)
center_col.grid(row=0, column=1, padx=12, pady=12, sticky="n")
# counters
counters_frame = ctk.CTkFrame(center_col, fg_color="#041f1c", corner_radius=8)
counters_frame.pack(padx=8, pady=8, fill="x")
ctk.CTkLabel(counters_frame, text="Results Summary", font=("Arial Black", 14), text_color="#ffd36e").pack(anchor="w", padx=6, pady=(6,4))
counter_labels = {}
for key in ["PLAYER","BANKER","TIE","PLAYER_PAIR","BANKER_PAIR","NATURAL","SUPER_SIX"]:
    lbl = ctk.CTkLabel(counters_frame, text=f"{key}: 0", anchor="w", font=("Consolas", 12))
    lbl.pack(fill="x", padx=8, pady=2)
    counter_labels[key] = lbl

# bead scoreboard frame (big)
bead_frame_outer = ctk.CTkFrame(center_col, fg_color="#021d18", corner_radius=10)
bead_frame_outer.pack(padx=8, pady=(10,8), fill="both")
ctk.CTkLabel(bead_frame_outer, text="Bead Plate (Big row view)", font=("Arial", 12), text_color="#bfe8d6").pack(anchor="w", padx=8, pady=(8,0))
bead_canvas = ctk.CTkCanvas(bead_frame_outer, height=220, highlightthickness=0, bg="#011814")
bead_canvas.pack(padx=8, pady=8, fill="both", expand=False)

# banker column
banker_col = ctk.CTkFrame(board, fg_color="#04221f", corner_radius=10)
banker_col.grid(row=0, column=2, padx=18, pady=12, sticky="n")
banker_label = ctk.CTkLabel(banker_col, text="BANKER", font=("Arial Black", 18), text_color="#ff9c9c")
banker_label.pack(padx=10, pady=(10,6))
b_cards_frame = ctk.CTkFrame(banker_col, fg_color="#021a17", corner_radius=8)
b_cards_frame.pack(padx=8, pady=6)
b_card_labels = [ctk.CTkLabel(b_cards_frame, text="", width=110, height=150, corner_radius=8, fg_color="#021a17") for _ in range(3)]
for lbl in b_card_labels:
    lbl.pack(side="left", padx=6, pady=10)
banker_score = ctk.CTkLabel(banker_col, text="Score: -", font=("Arial", 14))
banker_score.pack(pady=6)

# controls row
controls = ctk.CTkFrame(root, fg_color="#041f1c", corner_radius=8)
controls.pack(fill="x", padx=20, pady=(8,14))
status_label = ctk.CTkLabel(controls, text="Ready — waiting for serial input or manual (1/2/3)", font=("Arial", 13))
status_label.grid(row=0, column=0, padx=12, pady=8, sticky="w")
reset_btn = ctk.CTkButton(controls, text="New Round ( / )", width=160, command=lambda: reset_board())
reset_btn.grid(row=0, column=1, padx=6)
ctk.CTkButton(controls, text="Player (1)", width=120, command=lambda: manual_result("PLAYER")).grid(row=0, column=2, padx=6)
ctk.CTkButton(controls, text="Banker (2)", width=120, command=lambda: manual_result("BANKER")).grid(row=0, column=3, padx=6)
ctk.CTkButton(controls, text="Tie (3)", width=120, command=lambda: manual_result("TIE")).grid(row=0, column=4, padx=6)

# ------------------ Image helper (CTkImage) ------------------
def set_card_image(label, card_name):
    img_path = os.path.join(CARDS_DIR, f"{card_name}.png")
    if not os.path.exists(img_path):
        try:
            label.configure(text=card_name, image=None)
            label.image = None
        except Exception:
            pass
        return
    try:
        img = Image.open(img_path).convert("RGBA")
    except Exception as e:
        print("Image open error:", e)
        label.configure(text=card_name, image=None)
        label.image = None
        return
    target_w, target_h = 110, 150
    img_ratio = img.width / img.height
    if img_ratio > (target_w / target_h):
        new_w = target_w
        new_h = int(target_w / img_ratio)
    else:
        new_h = target_h
        new_w = int(target_h * img_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    try:
        ctk_img = CTkImage(light_image=img, dark_image=img, size=(new_w, new_h))
    except Exception as e:
        print("CTkImage creation error:", e)
        label.configure(text=card_name, image=None)
        label.image = None
        return
    key = f"{card_name}_{new_w}x{new_h}"
    _image_cache[key] = ctk_img
    try:
        label.configure(image=ctk_img, text="")
        label.image = ctk_img
    except Exception as e:
        print("Label configure image error:", e)

# ------------------ Popups & small animation ------------------
def show_popup(text):
    global winner_popup
    if winner_popup and winner_popup.winfo_exists():
        try:
            winner_popup.destroy()
        except Exception:
            pass
    winner_popup = ctk.CTkToplevel(root)
    winner_popup.overrideredirect(True)
    winner_popup.geometry("360x100")
    winner_popup.configure(fg_color="#00271f")
    lbl = ctk.CTkLabel(winner_popup, text=text, text_color="#ffd36e", font=("Arial Black", 22))
    lbl.pack(expand=True)
    x = root.winfo_screenwidth() // 2 - 180
    y = root.winfo_screenheight() // 2 - 50
    winner_popup.geometry(f"360x100+{x}+{y}")
    root.after(1400, lambda: winner_popup.destroy() if winner_popup and winner_popup.winfo_exists() else None)

# ------------------ Bead Grid drawing ------------------
def draw_bead_plate():
    """Draw bead plate on bead_canvas from bead_columns list.
       Each column is up to BEAD_ROWS items filled top->bottom.
    """
    canvas = bead_canvas
    canvas.delete("all")
    cols = max(1, len(bead_columns))
    cell_w = 36
    cell_h = 36
    pad_x = 8
    pad_y = 18
    width = cols * (cell_w + 8) + pad_x * 2
    height = BEAD_ROWS * (cell_h + 6) + pad_y * 2
    # resize canvas so it fits columns
    canvas.configure(width=min(width, 1200), height=height)
    # draw each cell
    for ci, col in enumerate(bead_columns):
        for ri in range(BEAD_ROWS):
            x = pad_x + ci * (cell_w + 8)
            y = pad_y + ri * (cell_h + 6)
            # background rect
            canvas.create_rectangle(x, y, x + cell_w, y + cell_h, fill="#02221b", outline="#00160f")
            if ri < len(col):
                val = col[ri]
                if val == "P":
                    fill = "#2bd6a6"
                    txt = "P"
                    txt_color = "#002218"
                elif val == "B":
                    fill = "#ff6b6b"
                    txt = "B"
                    txt_color = "#3a0000"
                else:
                    fill = "#cdd9b6"
                    txt = "T"
                    txt_color = "#07240f"
                # circle inside cell
                cx = x + cell_w//2
                cy = y + cell_h//2
                r = min(cell_w, cell_h)//2 - 4
                canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill=fill, outline="#001614")
                canvas.create_text(cx, cy, text=txt, fill=txt_color, font=("Consolas", 12, "bold"))

# function to append symbol to bead_columns
def append_bead(symbol):
    """Append a symbol (P/B/T) to bead_columns in bead-plate fill order (top->bottom, then next column)."""
    if not bead_columns:
        bead_columns.append([])
    last_col = bead_columns[-1]
    if len(last_col) < BEAD_ROWS:
        last_col.append(symbol)
    else:
        bead_columns.append([symbol])
    draw_bead_plate()
    # save compact history
    save_history_compact(symbol)

# ------------------ Logic ------------------
game_counter = 0

def evaluate_round():
    """Evaluate Baccarat result and derived outcomes."""
    global game_over, game_counter
    if len(deal_cards) < 4:
        return

    player_cards[:] = deal_cards[:2]
    banker_cards[:] = deal_cards[2:4]

    for i, c in enumerate(player_cards):
        set_card_image(p_card_labels[i], c)
    for i, c in enumerate(banker_cards):
        set_card_image(b_card_labels[i], c)

    p_total = compute_total(player_cards)
    b_total = compute_total(banker_cards)
    player_score.configure(text=f"Score: {p_total}")
    banker_score.configure(text=f"Score: {b_total}")

    if p_total == b_total:
        winner = "TIE"
    elif p_total > b_total:
        winner = "PLAYER"
    else:
        winner = "BANKER"

    # derived checks
    p_pair = (card_rank(player_cards[0]) == card_rank(player_cards[1]))
    b_pair = (card_rank(banker_cards[0]) == card_rank(banker_cards[1]))
    natural = (p_total in (8,9)) or (b_total in (8,9))
    super_six = (winner == "BANKER" and b_total == 6)

    # update counters
    counters[winner] = counters.get(winner, 0) + 1
    if p_pair: counters["PLAYER_PAIR"] += 1
    if b_pair: counters["BANKER_PAIR"] += 1
    if natural: counters["NATURAL"] += 1
    if super_six: counters["SUPER_SIX"] += 1

    # update UI counters
    for k, lbl in counter_labels.items():
        lbl.configure(text=f"{k}: {counters.get(k, 0)}")

    # append to bead grid
    short = "P" if winner == "PLAYER" else ("B" if winner == "BANKER" else "T")
    append_bead(short)

    # show popup and visual
    show_popup(f"{winner} WINS!" if winner != "TIE" else "TIE GAME")
    if winner == "PLAYER":
        player_label.configure(text="PLAYER ★", text_color="#b8ffd8")
    elif winner == "BANKER":
        banker_label.configure(text="BANKER ★", text_color="#ffd0d0")
    root.after(900, lambda: player_label.configure(text="PLAYER", text_color="#8ef0c6"))
    root.after(900, lambda: banker_label.configure(text="BANKER", text_color="#ff9c9c"))

    # log a compact history symbol to file only
    save_history_compact(short)

    game_over = True
    game_counter += 1
    game_num_label.configure(text=f"Game: {game_counter}")

def reset_board():
    global deal_cards, player_cards, banker_cards, game_over
    deal_cards.clear()
    player_cards.clear()
    banker_cards.clear()
    for lbl in p_card_labels + b_card_labels:
        try:
            lbl.configure(image=None, text="")
            lbl.image = None
        except Exception:
            pass
    player_score.configure(text="Score: -")
    banker_score.configure(text="Score: -")
    status_label.configure(text="🎲 New round started – waiting for cards or manual result…")
    game_over = False

def manual_result(winner):
    global game_over
    if game_over:
        return
    # create placeholder cards to compute derived results
    if winner == "PLAYER":
        deal_cards[:] = ["hearts_9", "clubs_1", "diamonds_2", "spades_1"]
    elif winner == "BANKER":
        deal_cards[:] = ["hearts_1", "clubs_1", "diamonds_8", "spades_8"]
    else:
        deal_cards[:] = ["hearts_4", "clubs_4", "diamonds_4", "spades_4"]
    game_over = False
    evaluate_round()

# ------------------ Keybinds ------------------
root.bind("/", lambda e: reset_board())
root.bind("1", lambda e: manual_result("PLAYER"))
root.bind("2", lambda e: manual_result("BANKER"))
root.bind("3", lambda e: manual_result("TIE"))

# ------------------ Serial Thread ------------------
def serial_reader():
    global game_over
    while not stop_event.is_set():
        if not ser:
            time.sleep(1)
            continue
        try:
            try:
                waiting = ser.in_waiting
            except Exception:
                waiting = 0
            if waiting > 0:
                raw = ser.readline().decode(errors="ignore").strip()
                if not raw:
                    continue
                if raw in card_map and not game_over:
                    card_name = card_map[raw]
                    deal_cards.append(card_name)
                    root.after(0, lambda name=card_name: status_label.configure(text=f"Dealt {name} ({len(deal_cards)}/4)"))
                    if len(deal_cards) <= 2:
                        idx = len(deal_cards) - 1
                        root.after(0, set_card_image, p_card_labels[idx], card_name)
                    elif len(deal_cards) <= 4:
                        idx = len(deal_cards) - 3
                        root.after(0, set_card_image, b_card_labels[idx], card_name)
                    if len(deal_cards) == 4:
                        root.after(300, evaluate_round)
        except Exception as e:
            print("Serial read error:", e)
            time.sleep(0.5)
        time.sleep(0.05)

# ------------------ Graceful Exit ------------------
def on_close():
    print("🛑 Closing game...")
    stop_event.set()
    try:
        if ser and getattr(ser, "is_open", False):
            try:
                ser.close()
            except Exception as e:
                print("Error closing serial:", e)
    except Exception as e:
        print("Error checking serial:", e)
    try:
        root.destroy()
    except Exception:
        pass

root.protocol("WM_DELETE_WINDOW", on_close)

# Start serial thread
_thread = threading.Thread(target=serial_reader, daemon=True)
_thread.start()

# initial draw
draw_bead_plate() if 'draw_bead_plate' in globals() else None

root.mainloop()
