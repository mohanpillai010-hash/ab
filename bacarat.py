import tkinter as tk
from tkinter import PhotoImage, Toplevel, Canvas, Frame, Scrollbar
import threading, serial, json, os, time

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
root.title("Mr. Pillai - Baccarat")
root.state("zoomed")
root.config(bg="#0f0f1a")

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
         font=("Arial", 32, "bold")).pack(pady=18)

# ------------------ Player / Banker UI ------------------
board_frame = tk.Frame(main_frame, bg="#0f0f1a")
board_frame.pack(pady=6)

player_frame = tk.Frame(board_frame, bg="#0f0f1a")
player_frame.grid(row=0, column=0, padx=40)
tk.Label(player_frame, text="PLAYER", fg="#66ff99", bg="#0f0f1a", font=("Arial", 20, "bold")).pack()
player_cards_frame = tk.Frame(player_frame, bg="#0f0f1a")
player_cards_frame.pack(pady=10)
p_card_labels = [tk.Label(player_cards_frame, bg="#0f0f1a") for _ in range(3)]
for lbl in p_card_labels:
    lbl.pack(side="left", padx=6)

player_score_label = tk.Label(player_frame, text="Score: -", fg="white", bg="#0f0f1a", font=("Arial", 16))
player_score_label.pack(pady=6)

banker_frame = tk.Frame(board_frame, bg="#0f0f1a")
banker_frame.grid(row=0, column=1, padx=40)
tk.Label(banker_frame, text="BANKER", fg="#ff6666", bg="#0f0f1a", font=("Arial", 20, "bold")).pack()
banker_cards_frame = tk.Frame(banker_frame, bg="#0f0f1a")
banker_cards_frame.pack(pady=10)
b_card_labels = [tk.Label(banker_cards_frame, bg="#0f0f1a") for _ in range(3)]
for lbl in b_card_labels:
    lbl.pack(side="left", padx=6)

banker_score_label = tk.Label(banker_frame, text="Score: -", fg="white", bg="#0f0f1a", font=("Arial", 16))
banker_score_label.pack(pady=6)

# ------------------ Controls / Status ------------------
controls_frame = tk.Frame(main_frame, bg="#0f0f1a")
controls_frame.pack(pady=6)
status_label = tk.Label(controls_frame, text="Waiting for serial input or press 1/2/3 for manual result",
                        fg="white", bg="#0f0f1a", font=("Arial", 14))
status_label.pack()

note_label = tk.Label(main_frame, text="Manual keys: 1=Player win, 2=Banker win, 3=Tie, / = reset",
                      fg="#DDD", bg="#0f0f1a", font=("Arial", 11))
note_label.pack(pady=2)

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
# We'll collect cards in order: P1, P2, B1, B2 (optionally third cards later)
deal_cards = []             # will hold card keys like 'club_7' (as strings from card_map)
player_cards = []           # will hold card names for player
banker_cards = []           # will hold card names for banker
winner_popup = None

# ------------------ Helper Utilities ------------------
def card_point_from_name(card_name):
    """Given card name like 'heart_ace' or 'club_10' return baccarat point value."""
    # assume card_name format contains rank after underscore
    # ranks might be 'ace', '2'...'10','jack','queen','king'
    parts = card_name.split('_')
    rank = parts[-1]
    if rank in ('jack', 'queen', 'king', '10'):
        return 0
    if rank == 'ace':
        return 1
    try:
        return int(rank)
    except:
        return 0

def compute_total(cards_list):
    s = sum(card_point_from_name(c) for c in cards_list)
    return s % 10

def reset_board():
    global deal_cards, player_cards, banker_cards
    deal_cards = []
    player_cards = []
    banker_cards = []
    # clear images
    for lbl in p_card_labels + b_card_labels:
        lbl.config(image="", text="")
        lbl.image = None
    player_score_label.config(text="Score: -")
    banker_score_label.config(text="Score: -")
    status_label.config(text="New round. Waiting for cards or manual result.")

def log_history_line(line):
    history_text.insert("end", line + "\n")
    history_text.see("end")
    print(line)

def show_result_popup(text):
    global winner_popup
    try:
        if winner_popup and winner_popup.winfo_exists():
            winner_popup.destroy()
    except:
        pass
    winner_popup = Toplevel(root)
    winner_popup.title("Result")
    winner_popup.geometry("360x120")
    winner_popup.config(bg="#0f0f1a")
    tk.Label(winner_popup, text=text, fg="#FFD700", bg="#0f0f1a",
             font=("Arial", 20, "bold")).pack(expand=True, pady=20)
    # auto close after 2s
    def close_it():
        try:
            if winner_popup and winner_popup.winfo_exists():
                winner_popup.destroy()
        except:
            pass
    root.after(2000, close_it)

# ------------------ Baccarat Flow (simplified 2-card evaluation) ------------------
def evaluate_baccarat_round():
    """Evaluate after 4 cards: P1,P2,B1,B2.
       This is a simplified implementation: handle naturals (8/9) and compare totals (mod 10).
       (No full third-card rules implemented here.)"""
    if len(deal_cards) < 4:
        return
    # first two -> player, next two -> banker
    player_cards[:] = deal_cards[0:2]
    banker_cards[:] = deal_cards[2:4]
    # update images
    for i, c in enumerate(player_cards):
        set_card_image(p_card_labels[i], c)
    for i, c in enumerate(banker_cards):
        set_card_image(b_card_labels[i], c)
    # scores
    p_total = compute_total(player_cards)
    b_total = compute_total(banker_cards)
    player_score_label.config(text=f"Score: {p_total}")
    banker_score_label.config(text=f"Score: {b_total}")
    status_label.config(text=f"Dealt 4 cards. Player {p_total} vs Banker {b_total}")

    # naturals (8 or 9)
    if p_total in (8,9) or b_total in (8,9):
        # winner is higher (or tie)
        if p_total > b_total:
            winner = "PLAYER"
        elif b_total > p_total:
            winner = "BANKER"
        else:
            winner = "TIE"
    else:
        # simplified: compare totals
        if p_total > b_total:
            winner = "PLAYER"
        elif b_total > p_total:
            winner = "BANKER"
        else:
            winner = "TIE"

    # log and popup
    line = f"Player: {','.join(player_cards)} ({p_total}) | Banker: {','.join(banker_cards)} ({b_total}) → {winner}"
    log_history_line(line)
    show_result_popup(f"{winner} WINS!")
    # after evaluation keep history but prevent further automatic evaluations until reset
    # set a flag to block repeated evaluation
    # We mark game_over to prevent manual or serial further inputs until reset
    global game_over
    game_over = True

# ------------------ UI helper to set card image from cards folder ------------------
def set_card_image(label, card_name):
    # card_name is assumed to be something like 'club_7' (exact filenames: club_7.png)
    img_path = os.path.join(CARDS_DIR, f"{card_name}.png")
    if os.path.exists(img_path):
        try:
            img = PhotoImage(file=img_path)
            # small scale to fit
            # compute simple scaling if huge:
            w, h = img.width(), img.height()
            max_w, max_h = 110, 160
            if w > max_w or h > max_h:
                sx = max(1, int(w / max_w))
                sy = max(1, int(h / max_h))
                img = img.subsample(max(sx, sy), max(sx, sy))
            label.config(image=img, text="")
            label.image = img
        except Exception as e:
            label.config(text=card_name, image="")
            label.image = None
    else:
        label.config(text=card_name, image="")
        label.image = None

# ------------------ Reset handler ------------------
def reset_all(event=None):
    global game_over
    # close popup safely
    try:
        if winner_popup and winner_popup.winfo_exists():
            winner_popup.destroy()
    except:
        pass
    game_over = False
    reset_board()
    status_label.config(text="Round reset. Waiting for cards or manual result.")
root.bind("/", reset_all)

# ------------------ Manual result keys ------------------
def manual_win_player(event=None):
    global game_over
    if game_over:
        return
    game_over = True
    log_history_line("Manual result → PLAYER")
    show_result_popup("PLAYER WINS!")
root.bind("1", manual_win_player)

def manual_win_banker(event=None):
    global game_over
    if game_over:
        return
    game_over = True
    log_history_line("Manual result → BANKER")
    show_result_popup("BANKER WINS!")
root.bind("2", manual_win_banker)

def manual_tie(event=None):
    global game_over
    if game_over:
        return
    game_over = True
    log_history_line("Manual result → TIE")
    show_result_popup("TIE")
root.bind("3", manual_tie)

# ------------------ Serial reader for Baccarat ------------------
def read_serial_baccarat():
    """Read cards from serial. Expect device to send card IDs that exist in card_map keys.
       We'll append to deal_cards and evaluate after 4 cards."""
    global game_over
    while True:
        if not ser:
            time.sleep(1)
            continue
        try:
            if ser.in_waiting > 0:
                raw = ser.readline()
                try:
                    data = raw.decode(errors="ignore").strip()
                except:
                    data = str(raw).strip()
                if not data:
                    continue
                # Debug
                print("Serial received:", repr(data))
                # normalize: some devices send number codes; assume those map in card_map
                key = data
                # if device sends numeric index, map accordingly (user already has card_map mapping)
                if key in card_map:
                    card_name = card_map[key]  # this is filename base like 'club_7'
                    # only accept cards when not game_over
                    if game_over:
                        # ignore until reset
                        continue
                    # append and update small UI indicator
                    deal_cards.append(card_name)
                    status_label.config(text=f"Dealt card: {card_name} ({len(deal_cards)}/4)")
                    # show in mini placeholders while waiting:
                    if len(deal_cards) <= 2:
                        # player card slots
                        set_card_image(p_card_labels[len(deal_cards)-1], card_name)
                    elif len(deal_cards) <= 4:
                        set_card_image(b_card_labels[len(deal_cards)-3], card_name)
                    # when 4 reached evaluate
                    if len(deal_cards) == 4:
                        # schedule evaluation on main thread
                        root.after(50, evaluate_baccarat_round)
                else:
                    # not recognized key, ignore or print
                    print("Unknown serial key:", repr(data))
        except Exception as e:
            print("Serial read error:", e)
            time.sleep(0.5)
        time.sleep(0.05)

threading.Thread(target=read_serial_baccarat, daemon=True).start()

# ------------------ Start UI ------------------
status_label.config(text="Ready. Waiting for serial cards or manual input (1/2/3).")
root.mainloop()
