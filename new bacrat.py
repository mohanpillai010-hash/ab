import tkinter as tk
from tkinter import PhotoImage, Toplevel, Canvas, Frame, Scrollbar
import threading, serial, json, os, time
from PIL import Image, ImageTk  # Pillow for image scaling

# ------------------ Configuration ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR = os.path.join(BASE_DIR, "cards")
with open(os.path.join(BASE_DIR, 'card_map.json'), 'r') as f:
    card_map = json.load(f)

# Serial port (safe open)
try:
    ser = serial.Serial('COM3', 9600, timeout=1)
    print("✅ Connected to serial port COM3")
except Exception as e:
    print("⚠️ Serial not connected:", e)
    ser = None

# ------------------ GUI Setup ------------------
root = tk.Tk()
root.title("🎴 Mr. Pillai — Baccarat (Casino Edition) 🎴")
root.state("zoomed")
root.config(bg="#0f0f1a")

# Animated casino background shimmer
def animate_background():
    colors = ["#0f0f1a", "#161629", "#0f0f1a", "#1b1b2f"]
    current = getattr(animate_background, "index", 0)
    root.config(bg=colors[current])
    animate_background.index = (current + 1) % len(colors)
    root.after(4000, animate_background)
animate_background.index = 0
root.after(1000, animate_background)

# ------------------ Scrollable Frame ------------------
main_canvas = Canvas(root, bg="#0f0f1a", highlightthickness=0)
main_canvas.pack(side="left", fill="both", expand=True)
scrollbar = Scrollbar(root, orient="vertical", command=main_canvas.yview)
scrollbar.pack(side="right", fill="y")
main_canvas.configure(yscrollcommand=scrollbar.set)

main_frame = Frame(main_canvas, bg="#0f0f1a")
main_canvas.create_window((0, 0), window=main_frame, anchor="nw")
main_frame.bind("<Configure>", lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
main_canvas.bind_all("<MouseWheel>", lambda e: main_canvas.yview_scroll(-1 * (e.delta // 120), "units"))

# ------------------ Title ------------------
tk.Label(main_frame, text="🎴 Mr. Pillai — BACCARAT 🎴", fg="#FFD700", bg="#0f0f1a",
         font=("Helvetica Neue", 40, "bold")).pack(pady=18)

# ------------------ Player / Banker UI ------------------
board_frame = tk.Frame(main_frame, bg="#0f0f1a")
board_frame.pack(pady=6)

def gold_label(master, text, color):
    return tk.Label(master, text=text, fg=color, bg="#0f0f1a", font=("Arial", 22, "bold"))

player_frame = tk.Frame(board_frame, bg="#0f0f1a", highlightthickness=2, highlightbackground="#FFD700")
player_frame.grid(row=0, column=0, padx=60)
gold_label(player_frame, "PLAYER", "#00ff99").pack()
player_cards_frame = tk.Frame(player_frame, bg="#0f0f1a")
player_cards_frame.pack(pady=10)
p_card_labels = [tk.Label(player_cards_frame, bg="#0f0f1a") for _ in range(3)]
for lbl in p_card_labels: lbl.pack(side="left", padx=6)
player_score_label = tk.Label(player_frame, text="Score: -", fg="white", bg="#0f0f1a", font=("Arial", 16))
player_score_label.pack(pady=6)

banker_frame = tk.Frame(board_frame, bg="#0f0f1a", highlightthickness=2, highlightbackground="#FFD700")
banker_frame.grid(row=0, column=1, padx=60)
gold_label(banker_frame, "BANKER", "#ff6666").pack()
banker_cards_frame = tk.Frame(banker_frame, bg="#0f0f1a")
banker_cards_frame.pack(pady=10)
b_card_labels = [tk.Label(banker_cards_frame, bg="#0f0f1a") for _ in range(3)]
for lbl in b_card_labels: lbl.pack(side="left", padx=6)
banker_score_label = tk.Label(banker_frame, text="Score: -", fg="white", bg="#0f0f1a", font=("Arial", 16))
banker_score_label.pack(pady=6)

# ------------------ Controls / Status ------------------
controls_frame = tk.Frame(main_frame, bg="#0f0f1a")
controls_frame.pack(pady=6)
status_label = tk.Label(controls_frame, text="Waiting for serial input or press 1/2/3 for manual result",
                        fg="#FFD700", bg="#0f0f1a", font=("Arial", 14, "bold"))
status_label.pack()

note_label = tk.Label(main_frame, text="Manual keys: 1=Player win, 2=Banker win, 3=Tie, / = reset",
                      fg="#CCC", bg="#0f0f1a", font=("Arial", 11))
note_label.pack(pady=4)

# ------------------ Game History ------------------
history_frame = tk.Frame(main_frame, bg="#1a1a2e")
history_frame.pack(pady=10, fill="x", padx=30)
tk.Label(history_frame, text="📜 Game History", fg="#FFD700", bg="#1a1a2e",
         font=("Arial", 18, "bold")).pack(anchor="w", padx=10, pady=5)
history_text = tk.Text(history_frame, height=10, bg="#0f0f1a", fg="#00ffff",
                       font=("Consolas", 12), relief="flat", wrap="none")
history_text.pack(fill="x", padx=10, pady=5)
scrollbar_history = tk.Scrollbar(history_frame, command=history_text.yview)
scrollbar_history.pack(side="right", fill="y")
history_text.config(yscrollcommand=scrollbar_history.set)

# ------------------ Baccarat State ------------------
deal_cards, player_cards, banker_cards = [], [], []
winner_popup = None
game_over = False

# ------------------ Helper Utilities ------------------
def card_point_from_name(card_name):
    rank = card_name.split('_')[-1]
    if rank in ('jack', 'queen', 'king', '10'): return 0
    if rank == 'ace': return 1
    try: return int(rank)
    except: return 0

def compute_total(cards_list):
    return sum(card_point_from_name(c) for c in cards_list) % 10

def log_history_line(line):
    history_text.insert("end", line + "\n")
    history_text.see("end")
    print(line)

# ------------------ UI Enhancements ------------------
def set_card_image(label, card_name, slide_in=True, flip=True):
    img_path = os.path.join(CARDS_DIR, f"{card_name}.png")
    if not os.path.exists(img_path):
        label.config(text=card_name, image=""); return
    try:
        img = Image.open(img_path)
        img.thumbnail((110, 160))
        tk_img = ImageTk.PhotoImage(img)
        label.image = tk_img

        if flip:
            label.config(text="", image="")
            def reveal():
                label.config(image=tk_img)
            root.after(400, reveal)
        else:
            label.config(image=tk_img)

        if slide_in:
            x_pos = -150
            label.place(x=x_pos)
            def slide():
                nonlocal x_pos
                x_pos += 15
                label.place(x=x_pos)
                if x_pos < 0:
                    root.after(10, slide)
                else:
                    label.place(x=0)
            root.after(100, slide)
    except Exception as e:
        label.config(text=card_name, image="")

def highlight_winner(winner):
    frame = player_frame if winner == "PLAYER" else banker_frame
    color = "#00ff99" if winner == "PLAYER" else "#ff4444"
    def flash(times=6):
        if times <= 0:
            frame.config(highlightbackground="#FFD700")
            return
        frame.config(highlightbackground=color if times % 2 else "#FFD700")
        root.after(200, lambda: flash(times - 1))
    flash()

def show_result_popup(text):
    global winner_popup
    try:
        if winner_popup and winner_popup.winfo_exists(): winner_popup.destroy()
    except: pass
    winner_popup = Toplevel(root)
    winner_popup.overrideredirect(True)
    winner_popup.config(bg="#1a1a2e")
    label = tk.Label(winner_popup, text=text, fg="#FFD700", bg="#1a1a2e", font=("Arial Black", 26))
    label.pack(padx=20, pady=30)
    # start offscreen and slide in
    x = root.winfo_screenwidth()
    y = root.winfo_screenheight() // 2 - 60
    winner_popup.geometry(f"400x120+{x}+{y}")
    def slide_in():
        nonlocal x
        x -= 40
        winner_popup.geometry(f"400x120+{x}+{y}")
        if x > root.winfo_screenwidth() - 450:
            root.after(15, slide_in)
    slide_in()
    root.after(2000, winner_popup.destroy)

def reset_board():
    global deal_cards, player_cards, banker_cards
    deal_cards, player_cards, banker_cards = [], [], []
    for lbl in p_card_labels + b_card_labels:
        lbl.config(image="", text=""); lbl.image = None
    player_score_label.config(text="Score: -")
    banker_score_label.config(text="Score: -")
    status_label.config(text="🎲 New round started. Waiting for cards or manual result...")

# ------------------ Game Logic ------------------
def evaluate_baccarat_round():
    global game_over
    if len(deal_cards) < 4: return
    player_cards[:] = deal_cards[0:2]
    banker_cards[:] = deal_cards[2:4]

    for i, c in enumerate(player_cards): set_card_image(p_card_labels[i], c)
    for i, c in enumerate(banker_cards): set_card_image(b_card_labels[i], c)

    p_total, b_total = compute_total(player_cards), compute_total(banker_cards)
    player_score_label.config(text=f"Score: {p_total}")
    banker_score_label.config(text=f"Score: {b_total}")

    if p_total in (8, 9) or b_total in (8, 9):
        winner = "PLAYER" if p_total > b_total else "BANKER" if b_total > p_total else "TIE"
    else:
        winner = "PLAYER" if p_total > b_total else "BANKER" if b_total > p_total else "TIE"

    log_history_line(f"Player: {','.join(player_cards)} ({p_total}) | Banker: {','.join(banker_cards)} ({b_total}) → {winner}")
    show_result_popup(f"{winner} WINS!" if winner != "TIE" else "TIE GAME")
    if winner != "TIE": highlight_winner(winner)
    game_over = True

# ------------------ Key Handlers ------------------
def reset_all(event=None):
    global game_over
    try:
        if winner_popup and winner_popup.winfo_exists(): winner_popup.destroy()
    except: pass
    game_over = False
    reset_board()
root.bind("/", reset_all)

def manual_result(winner):
    global game_over
    if game_over: return
    game_over = True
    log_history_line(f"Manual result → {winner}")
    show_result_popup(f"{winner} WINS!" if winner != "TIE" else "TIE")
    if winner != "TIE": highlight_winner(winner)

root.bind("1", lambda e: manual_result("PLAYER"))
root.bind("2", lambda e: manual_result("BANKER"))
root.bind("3", lambda e: manual_result("TIE"))

# ------------------ Serial Thread ------------------
def read_serial_baccarat():
    global game_over
    while True:
        if not ser:
            time.sleep(1); continue
        try:
            if ser.in_waiting > 0:
                raw = ser.readline()
                data = raw.decode(errors="ignore").strip()
                if not data: continue
                if data in card_map:
                    if game_over: continue
                    card_name = card_map[data]
                    deal_cards.append(card_name)
                    status_label.config(text=f"Dealt card: {card_name} ({len(deal_cards)}/4)")
                    if len(deal_cards) <= 2:
                        set_card_image(p_card_labels[len(deal_cards)-1], card_name)
                    elif len(deal_cards) <= 4:
                        set_card_image(b_card_labels[len(deal_cards)-3], card_name)
                    if len(deal_cards) == 4:
                        root.after(50, evaluate_baccarat_round)
        except Exception as e:
            print("Serial read error:", e)
            time.sleep(0.5)
        time.sleep(0.05)

threading.Thread(target=read_serial_baccarat, daemon=True).start()

# ------------------ Start ------------------
status_label.config(text="Ready 🎯 Waiting for serial cards or manual input (1/2/3).")
root.mainloop()
