# mb_casino_minimal.py
import customtkinter as ctk
from customtkinter import CTkImage
import threading, serial, json, os, time
from PIL import Image, ImageDraw

# ------------------ Setup ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR = os.path.join(BASE_DIR, "cards")

with open(os.path.join(BASE_DIR, "card_map.json"), "r", encoding="utf-8") as f:
    card_map = json.load(f)

# Serial connection (same as before)
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
root.title("🎴 Mr. Pillai — Baccarat (Minimal Casino UI)")
try:
    root.state("zoomed")
except Exception:
    pass
root.configure(fg_color="#071a13")

# ------------------ State ------------------
deal_cards, player_cards, banker_cards = [], [], []
game_over = False
winner_popup = None

# Derived counters
counters = {
    "PLAYER": 0,
    "BANKER": 0,
    "TIE": 0,
    "PLAYER_PAIR": 0,
    "BANKER_PAIR": 0,
    "NATURAL": 0,
    "SUPER_SIX": 0
}

# Keep a global image cache so images are not garbage-collected
_image_cache = {}

# Thread stop event for graceful exit
stop_event = threading.Event()

# Cockroach Road data (simple linear layout)
cockroach_sequence = []  # list of 'P','B','T'

# ------------------ Helpers ------------------
def card_rank(card_name: str):
    """Return canonical rank string from card filename (ace,2,..,10,jack,queen,king)."""
    name = os.path.splitext(os.path.basename(card_name))[0].lower()
    if "_" in name:
        rank = name.split("_")[-1]
    else:
        rank = ''.join(ch for ch in name if ch.isalnum()).rstrip("shcd")
    return rank

def card_point(card_name: str):
    """Return Baccarat value (Ace=1, 2–9=face value, 10/J/Q/K=0)."""
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
    """Compute Baccarat total (mod 10)."""
    return sum(card_point(c) for c in cards) % 10

def log_history(line):
    """Append to history textbox and safely write to file in utf-8."""
    try:
        history_text.insert("end", line + "\n")
        history_text.see("end")
    except Exception:
        pass
    try:
        with open(os.path.join(BASE_DIR, "baccarat_history.txt"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print("History write error:", e)
    print(line)

# ------------------ Layout (minimal but clear) ------------------
top_frame = ctk.CTkFrame(root, fg_color="#07281f", corner_radius=16)
top_frame.pack(fill="x", padx=24, pady=(18, 6))

title = ctk.CTkLabel(top_frame, text="BACCARAT", font=("Arial Black", 36),
                     text_color="#bce0c6")
title.grid(row=0, column=0, sticky="w", padx=18, pady=8)

game_num_label = ctk.CTkLabel(top_frame, text="Game: 0", font=("Arial", 18),
                              text_color="#ffd36e")
game_num_label.grid(row=0, column=1, sticky="e", padx=18)

board = ctk.CTkFrame(root, fg_color="#052a22", corner_radius=16)
board.pack(fill="x", padx=24, pady=8)

# Left: Player
player_col = ctk.CTkFrame(board, fg_color="#042f2a", corner_radius=12)
player_col.grid(row=0, column=0, padx=20, pady=12, sticky="n")
player_label = ctk.CTkLabel(player_col, text="PLAYER", font=("Arial Black", 18),
                            text_color="#8ef0c6")
player_label.pack(padx=10, pady=(8,4))
p_cards_frame = ctk.CTkFrame(player_col, fg_color="#021a17", corner_radius=8)
p_cards_frame.pack(padx=8, pady=6)
p_card_labels = [ctk.CTkLabel(p_cards_frame, text="", width=110, height=150,
                              corner_radius=8, fg_color="#021a17")
                 for _ in range(3)]
for lbl in p_card_labels:
    lbl.pack(side="left", padx=6, pady=10)
player_score = ctk.CTkLabel(player_col, text="Score: -", font=("Arial", 14))
player_score.pack(pady=6)

# Center: Info & counters
center_col = ctk.CTkFrame(board, fg_color="#041f1c", corner_radius=8)
center_col.grid(row=0, column=1, padx=12, pady=12, sticky="n")
# Counters
counters_frame = ctk.CTkFrame(center_col, fg_color="#041f1c", corner_radius=8)
counters_frame.pack(padx=8, pady=8, fill="x")
ctk.CTkLabel(counters_frame, text="Results Summary", font=("Arial Black", 14),
             text_color="#ffd36e").pack(anchor="w", padx=6, pady=(6,4))
counter_labels = {}
for key in ["PLAYER", "BANKER", "TIE", "PLAYER_PAIR", "BANKER_PAIR", "NATURAL", "SUPER_SIX"]:
    lbl = ctk.CTkLabel(counters_frame, text=f"{key}: 0", anchor="w", font=("Consolas", 12))
    lbl.pack(fill="x", padx=8, pady=2)
    counter_labels[key] = lbl

# History text (narrow central)
ctk.CTkLabel(center_col, text="History", font=("Arial", 12), text_color="#bfe8d6").pack(anchor="w", padx=6)
history_text = ctk.CTkTextbox(center_col, height=140, fg_color="#011814", text_color="#8fffd6", font=("Consolas", 11))
history_text.pack(padx=6, pady=6, fill="x")

# Right: Banker
banker_col = ctk.CTkFrame(board, fg_color="#04221f", corner_radius=12)
banker_col.grid(row=0, column=2, padx=20, pady=12, sticky="n")
banker_label = ctk.CTkLabel(banker_col, text="BANKER", font=("Arial Black", 18),
                            text_color="#ff9c9c")
banker_label.pack(padx=10, pady=(8,4))
b_cards_frame = ctk.CTkFrame(banker_col, fg_color="#021a17", corner_radius=8)
b_cards_frame.pack(padx=8, pady=6)
b_card_labels = [ctk.CTkLabel(b_cards_frame, text="", width=110, height=150,
                              corner_radius=8, fg_color="#021a17")
                 for _ in range(3)]
for lbl in b_card_labels:
    lbl.pack(side="left", padx=6, pady=10)
banker_score = ctk.CTkLabel(banker_col, text="Score: -", font=("Arial", 14))
banker_score.pack(pady=6)

# Status and controls
controls = ctk.CTkFrame(root, fg_color="#041f1c", corner_radius=10)
controls.pack(fill="x", padx=24, pady=(6,10))
status_label = ctk.CTkLabel(controls, text="Ready — waiting for serial input or manual (1/2/3)",
                            font=("Arial", 13))
status_label.grid(row=0, column=0, padx=12, pady=10, sticky="w")
reset_btn = ctk.CTkButton(controls, text="New Round ( / )", width=160, command=lambda: reset_board())
reset_btn.grid(row=0, column=1, padx=6, pady=10)
# manual result buttons
ctk.CTkButton(controls, text="Player (1)", width=120, command=lambda: manual_result("PLAYER")).grid(row=0, column=2, padx=6)
ctk.CTkButton(controls, text="Banker (2)", width=120, command=lambda: manual_result("BANKER")).grid(row=0, column=3, padx=6)
ctk.CTkButton(controls, text="Tie (3)", width=120, command=lambda: manual_result("TIE")).grid(row=0, column=4, padx=6)

# Cockroach Road canvas (simple grid)
cockroach_frame = ctk.CTkFrame(root, fg_color="#041e1b", corner_radius=10)
cockroach_frame.pack(fill="both", padx=24, pady=(0,18), expand=False)
ctk.CTkLabel(cockroach_frame, text="Cockroach Road (simple view)", font=("Arial", 12), text_color="#bfe8d6").pack(anchor="w", padx=8, pady=6)
cockroach_canvas = ctk.CTkCanvas(cockroach_frame, width=900, height=160, highlightthickness=0, bg="#011814")
cockroach_canvas.pack(padx=12, pady=6)

# ------------------ Animations & Images (reuse previous approach) ------------------
def set_card_image(label, card_name):
    """Load card image safely and resize, using CTkImage so CTkLabel can scale properly."""
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

def show_popup(text):
    """Small popup on center for winners."""
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
    root.after(1600, lambda: winner_popup.destroy() if winner_popup and winner_popup.winfo_exists() else None)

# ------------------ Cockroach Road drawing (minimal) ------------------
def draw_cockroach():
    """Draw a simple grid with colored circles for P/B/T.
       Arranges items left->right then next row when column full.
    """
    canvas = cockroach_canvas
    canvas.delete("all")
    cols = 30  # how many columns per row
    cell_w, cell_h = 26, 26
    margin_x, margin_y = 8, 8
    # draw background grid
    width = cols * (cell_w + 4) + margin_x * 2
    # ensure canvas is big enough
    canvas.configure(width=width)
    for idx, val in enumerate(cockroach_sequence):
        col = idx % cols
        row = idx // cols
        x = margin_x + col * (cell_w + 4)
        y = margin_y + row * (cell_h + 6)
        # circle center
        cx, cy = x + cell_w//2, y + cell_h//2
        if val == "P":
            fill = "#2bd6a6"  # blue/green
        elif val == "B":
            fill = "#ff6b6b"  # red
        else:
            fill = "#9fffa3"  # tie greenish
        # outline
        canvas.create_oval(cx-10, cy-10, cx+10, cy+10, fill=fill, outline="#001914", width=1)
    # small legend
    canvas.create_text(60, 140, text="P: Player  B: Banker  T: Tie", fill="#cfeee0", anchor="w", font=("Consolas", 10))

# ------------------ Game Logic ------------------
game_counter = 0

def evaluate_round():
    """Evaluate Baccarat result and derived outcomes, update counters and UI."""
    global game_over, game_counter
    if len(deal_cards) < 4:
        return

    player_cards[:] = deal_cards[:2]
    banker_cards[:] = deal_cards[2:4]

    # set card visuals
    for i, c in enumerate(player_cards):
        set_card_image(p_card_labels[i], c)
    for i, c in enumerate(banker_cards):
        set_card_image(b_card_labels[i], c)

    p_total = compute_total(player_cards)
    b_total = compute_total(banker_cards)
    player_score.configure(text=f"Score: {p_total}")
    banker_score.configure(text=f"Score: {b_total}")

    # determine winner
    if p_total == b_total:
        winner = "TIE"
    elif p_total > b_total:
        winner = "PLAYER"
    else:
        winner = "BANKER"

    # derived checks
    # Pair: first two cards same rank
    p_pair = (card_rank(player_cards[0]) == card_rank(player_cards[1]))
    b_pair = (card_rank(banker_cards[0]) == card_rank(banker_cards[1]))
    # Natural: either initial total 8 or 9
    natural = (p_total in (8,9)) or (b_total in (8,9))
    # Super Six: Banker wins with total 6 (simple detection)
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

    # update cockroach road (simple append)
    short = "P" if winner == "PLAYER" else ("B" if winner == "BANKER" else "T")
    cockroach_sequence.append(short)
    # draw cockroach
    draw_cockroach()

    # logging summary
    summary = f"Game {game_counter+1}: Player {','.join(player_cards)} ({p_total}) vs Banker {','.join(banker_cards)} ({b_total}) => {winner}"
    extras = []
    if p_pair: extras.append("PLAYER_PAIR")
    if b_pair: extras.append("BANKER_PAIR")
    if natural: extras.append("NATURAL")
    if super_six: extras.append("SUPER_SIX")
    if extras:
        summary += " [" + ", ".join(extras) + "]"
    log_history(summary)

    # popup and glow
    show_popup(f"{winner} WINS!" if winner != "TIE" else "TIE GAME")
    if winner == "PLAYER":
        player_label.configure(text="PLAYER ★", text_color="#b8ffd8")
    elif winner == "BANKER":
        banker_label.configure(text="BANKER ★", text_color="#ffd0d0")
    # small visual reset to plain after delay
    root.after(900, lambda: player_label.configure(text="PLAYER", text_color="#8ef0c6"))
    root.after(900, lambda: banker_label.configure(text="BANKER", text_color="#ff9c9c"))

    game_over = True
    game_counter += 1
    game_num_label.configure(text=f"Game: {game_counter}")

def reset_board():
    """Clear all cards and start a new round."""
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

# ------------------ Manual Result ------------------
def manual_result(winner):
    global game_over
    if game_over:
        return
    # for manual result we just create placeholder cards to compute derived results
    # placeholder card names must exist as valid entries in your card set; we'll use 'spades_1' style
    # but to keep it minimal we only set totals via dummy small cards: choose sensible defaults
    if winner == "PLAYER":
        # example: give player higher total
        deal_cards[:] = ["hearts_9", "clubs_9", "diamonds_2", "spades_1"]
    elif winner == "BANKER":
        deal_cards[:] = ["hearts_2", "clubs_1", "diamonds_8", "spades_8"]
    else:
        deal_cards[:] = ["hearts_4", "clubs_4", "diamonds_4", "spades_4"]
    game_over = False
    # evaluate immediately
    evaluate_round()

# ------------------ Keybinds ------------------
root.bind("/", lambda e: reset_board())
root.bind("1", lambda e: manual_result("PLAYER"))
root.bind("2", lambda e: manual_result("BANKER"))
root.bind("3", lambda e: manual_result("TIE"))

# ------------------ Serial Thread ------------------
def serial_reader():
    """Background thread for reading serial card data (unchanged)."""
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
                    root.after(0, lambda name=card_name: status_label.configure(
                        text=f"Dealt {name} ({len(deal_cards)}/4)"
                    ))
                    # place card visuals
                    if len(deal_cards) <= 2:
                        idx = len(deal_cards) - 1
                        root.after(0, set_card_image, p_card_labels[idx], card_name)
                    elif len(deal_cards) <= 4:
                        idx = len(deal_cards) - 3
                        root.after(0, set_card_image, b_card_labels[idx], card_name)
                    if len(deal_cards) == 4:
                        # small delay before evaluation for UX
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

# Start the serial reader thread
_thread = threading.Thread(target=serial_reader, daemon=True)
_thread.start()

# draw initial cockroach
draw_cockroach()

root.mainloop()
