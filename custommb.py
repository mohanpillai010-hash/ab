import customtkinter as ctk
from tkinter import PhotoImage
import threading, serial, json, os, time
from PIL import Image, ImageTk

# ------------------ Setup ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR = os.path.join(BASE_DIR, "cards")
with open(os.path.join(BASE_DIR, "card_map.json"), "r") as f:
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
root.title("🎴 Mr. Pillai — Baccarat (CTk Casino Edition)")
root.state("zoomed")
root.configure(fg_color="#013220")  # Dark green background

# ------------------ State ------------------
deal_cards, player_cards, banker_cards = [], [], []
game_over = False
winner_popup = None

# ------------------ Helpers ------------------
def card_point(card_name):
    rank = card_name.split("_")[-1]
    if rank in ("jack", "queen", "king", "10"):
        return 0
    if rank == "ace":
        return 1
    try:
        return int(rank)
    except:
        return 0

def compute_total(cards):
    return sum(card_point(c) for c in cards) % 10

def log_history(line):
    history_text.insert("end", line + "\n")
    history_text.see("end")
    print(line)

# ------------------ Layout ------------------
title = ctk.CTkLabel(root, text="🎴 Mr. Pillai — BACCARAT 🎴",
                     font=("Arial Black", 42), text_color="#FFD700")
title.pack(pady=20)

board = ctk.CTkFrame(root, fg_color="#004d26", corner_radius=20)  # Deep green
board.pack(pady=10, padx=20, fill="x")

# Player frame
player_frame = ctk.CTkFrame(board, corner_radius=15, fg_color="#025f2d")
player_frame.grid(row=0, column=0, padx=60, pady=10)
ctk.CTkLabel(player_frame, text="PLAYER", font=("Arial Black", 20),
             text_color="#00FF99").pack(pady=5)
p_card_labels = [ctk.CTkLabel(player_frame, text="", width=120, height=160,
                              corner_radius=8, fg_color="#013220")
                 for _ in range(3)]
for lbl in p_card_labels:
    lbl.pack(side="left", padx=8, pady=10)
player_score = ctk.CTkLabel(player_frame, text="Score: -", text_color="white")
player_score.pack(pady=5)

# Banker frame
banker_frame = ctk.CTkFrame(board, corner_radius=15, fg_color="#025f2d")
banker_frame.grid(row=0, column=1, padx=60, pady=10)
ctk.CTkLabel(banker_frame, text="BANKER", font=("Arial Black", 20),
             text_color="#FF6666").pack(pady=5)
b_card_labels = [ctk.CTkLabel(banker_frame, text="", width=120, height=160,
                              corner_radius=8, fg_color="#013220")
                 for _ in range(3)]
for lbl in b_card_labels:
    lbl.pack(side="left", padx=8, pady=10)
banker_score = ctk.CTkLabel(banker_frame, text="Score: -", text_color="white")
banker_score.pack(pady=5)

# Status
status_label = ctk.CTkLabel(root,
    text="Ready. Waiting for serial input or manual result (1/2/3)",
    font=("Arial", 16), text_color="#FFD700")
status_label.pack(pady=10)

# History
history_frame = ctk.CTkFrame(root, fg_color="#004d26", corner_radius=15)
history_frame.pack(padx=30, pady=15, fill="x")
ctk.CTkLabel(history_frame, text="📜 Game History", font=("Arial Black", 20),
             text_color="#FFD700").pack(anchor="w", padx=15, pady=8)
history_text = ctk.CTkTextbox(history_frame, height=180, fg_color="#013220",
                              text_color="#00ffff", font=("Consolas", 12))
history_text.pack(fill="x", padx=15, pady=5)

# ------------------ Animations ------------------
def set_card_image(label, card_name):
    """Load card image, scale to fit neatly without distortion."""
    img_path = os.path.join(CARDS_DIR, f"{card_name}.png")
    if not os.path.exists(img_path):
        label.configure(text=card_name, image=None)
        return

    img = Image.open(img_path)
    img_ratio = img.width / img.height
    target_w, target_h = 120, 160

    # Maintain aspect ratio properly
    if img_ratio > (target_w / target_h):
        new_w = target_w
        new_h = int(target_w / img_ratio)
    else:
        new_h = target_h
        new_w = int(target_h * img_ratio)

    img = img.resize((new_w, new_h), Image.LANCZOS)
    tk_img = ImageTk.PhotoImage(img)
    label.configure(image=tk_img, text="")
    label.image = tk_img  # prevent garbage collection

def glow_winner(frame, color):
    """Simple glow pulse for winner highlight."""
    def pulse(i=0):
        alpha = (abs((i % 20) - 10)) / 10
        fg = f"#{int(alpha*255):02x}{int(alpha*255):02x}{int(alpha*255):02x}"
        frame.configure(border_color=color, border_width=3)
        if i < 40:
            root.after(60, lambda: pulse(i + 1))
        else:
            frame.configure(border_width=0)
    pulse()

def show_popup(text):
    """Slide-in animated popup for winner."""
    global winner_popup
    if winner_popup and winner_popup.winfo_exists():
        winner_popup.destroy()
    winner_popup = ctk.CTkToplevel(root)
    winner_popup.overrideredirect(True)
    winner_popup.geometry("420x140")
    winner_popup.configure(fg_color="#002d13")
    lbl = ctk.CTkLabel(winner_popup, text=text, text_color="#FFD700",
                       font=("Arial Black", 32))
    lbl.pack(expand=True)
    x = root.winfo_screenwidth()
    y = root.winfo_screenheight() // 2 - 70
    winner_popup.geometry(f"420x140+{x}+{y}")
    def slide():
        nonlocal x
        x -= 30
        winner_popup.geometry(f"420x140+{x}+{y}")
        if x > root.winfo_screenwidth() - 500:
            root.after(15, slide)
    slide()
    root.after(2000, winner_popup.destroy)

# ------------------ Logic ------------------
def evaluate_round():
    global game_over
    if len(deal_cards) < 4:
        return
    player_cards[:] = deal_cards[:2]
    banker_cards[:] = deal_cards[2:4]
    for i, c in enumerate(player_cards):
        set_card_image(p_card_labels[i], c)
    for i, c in enumerate(banker_cards):
        set_card_image(b_card_labels[i], c)
    p_total, b_total = compute_total(player_cards), compute_total(banker_cards)
    player_score.configure(text=f"Score: {p_total}")
    banker_score.configure(text=f"Score: {b_total}")
    winner = "TIE"
    if p_total != b_total:
        winner = "PLAYER" if p_total > b_total else "BANKER"
    log_history(f"Player: {','.join(player_cards)} ({p_total}) | "
                f"Banker: {','.join(banker_cards)} ({b_total}) → {winner}")
    show_popup(f"{winner} WINS!" if winner != "TIE" else "TIE GAME")
    if winner == "PLAYER":
        glow_winner(player_frame, "#00FF99")
    elif winner == "BANKER":
        glow_winner(banker_frame, "#FF4444")
    game_over = True

def reset_board():
    global deal_cards, player_cards, banker_cards, game_over
    deal_cards.clear(); player_cards.clear(); banker_cards.clear()
    for lbl in p_card_labels + b_card_labels:
        lbl.configure(image=None, text=""); lbl.image = None
    player_score.configure(text="Score: -")
    banker_score.configure(text="Score: -")
    status_label.configure(text="🎲 New round started – waiting for cards or manual result…")
    game_over = False

# ------------------ Keybinds ------------------
root.bind("/", lambda e: reset_board())
root.bind("1", lambda e: manual_result("PLAYER"))
root.bind("2", lambda e: manual_result("BANKER"))
root.bind("3", lambda e: manual_result("TIE"))

def manual_result(winner):
    global game_over
    if game_over: return
    game_over = True
    log_history(f"Manual result → {winner}")
    show_popup(f"{winner} WINS!" if winner != "TIE" else "TIE GAME")
    if winner == "PLAYER":
        glow_winner(player_frame, "#00FF99")
    elif winner == "BANKER":
        glow_winner(banker_frame, "#FF4444")

# ------------------ Serial Thread ------------------
def serial_reader():
    global game_over
    while True:
        if not ser:
            time.sleep(1); continue
        try:
            if ser.in_waiting > 0:
                raw = ser.readline().decode(errors="ignore").strip()
                if not raw: continue
                if raw in card_map and not game_over:
                    card_name = card_map[raw]
                    deal_cards.append(card_name)
                    status_label.configure(text=f"Dealt {card_name} ({len(deal_cards)}/4)")
                    if len(deal_cards) <= 2:
                        set_card_image(p_card_labels[len(deal_cards)-1], card_name)
                    elif len(deal_cards) <= 4:
                        set_card_image(b_card_labels[len(deal_cards)-3], card_name)
                    if len(deal_cards) == 4:
                        root.after(100, evaluate_round)
        except Exception as e:
            print("Serial read error:", e)
            time.sleep(0.5)
        time.sleep(0.05)

threading.Thread(target=serial_reader, daemon=True).start()
root.mainloop()
