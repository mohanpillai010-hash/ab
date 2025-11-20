# mb_andarbahar_modern_ctk.py
import customtkinter as ctk
from customtkinter import CTkImage
import threading, serial, json, os, time
from PIL import Image

# ------------------ Setup ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR = os.path.join(BASE_DIR, "cards")

with open(os.path.join(BASE_DIR, 'card_map.json'), 'r', encoding='utf-8') as f:
    card_map = json.load(f)

# Serial connection (don't crash if not present)
try:
    ser = serial.Serial('COM3', 9600, timeout=0)  # timeout 0 = non-blocking
    print("✅ Connected to serial port COM3")
except Exception as e:
    print("⚠️ Serial not connected:", e)
    ser = None

# ------------------ CTk setup ------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

root = ctk.CTk()
root.title("Mr. Pillai - Andar Bahar (Modern)")
try:
    root.state("zoomed")
except Exception:
    root.geometry("1280x720")
root.configure(fg_color="#071a13")

# ------------------ State ------------------
joker_card = None
side_toggle = True  # True -> ANDAR, False -> BAHAR
game_over = False
winner_popup = None

BEAD_ROWS = 6
bead_columns = []
game_counter = 0
_image_cache = {}
stop_event = threading.Event()


# ------------------ Helpers ------------------
def card_rank(card_name: str):
    name = os.path.splitext(os.path.basename(card_name))[0].lower()
    if "_" in name:
        rank = name.split("_")[-1]
    else:
        rank = ''.join(ch for ch in name if ch.isalnum()).rstrip("shcd")
    return rank


def save_history_compact(symbol):
    try:
        with open(os.path.join(BASE_DIR, "andar_history.txt"), "a", encoding="utf-8") as f:
            f.write(symbol + "\n")
    except:
        pass


# ------------------ Layout ------------------
header = ctk.CTkFrame(root, fg_color="#06241d", corner_radius=10)
header.pack(fill="x", padx=16, pady=(12, 8))
ctk.CTkLabel(header, text="ANDAR BAHAR", font=("Arial Black", 34), text_color="#bce0c6").grid(row=0, column=0,
                                                                                              sticky="w", padx=12,
                                                                                              pady=10)
game_label = ctk.CTkLabel(header, text="Game: 0", font=("Arial", 14), text_color="#ffd36e")
game_label.grid(row=0, column=1, sticky="e", padx=12)

board = ctk.CTkFrame(root, fg_color="#052a22", corner_radius=12)
board.pack(fill="x", padx=16, pady=8)

# Joker
joker_col = ctk.CTkFrame(board, fg_color="#042f2a", corner_radius=10)
joker_col.grid(row=0, column=0, padx=18, pady=12)
ctk.CTkLabel(joker_col, text="JOKER", font=("Arial Black", 18), text_color="#ffd36e").pack(pady=(10, 6))
joker_img = ctk.CTkLabel(joker_col, text="", width=160, height=220, fg_color="#021a17")
joker_img.pack(padx=10, pady=6)
joker_text = ctk.CTkLabel(joker_col, text="Waiting...", font=("Arial", 12), text_color="#8fffd6")
joker_text.pack(pady=(6, 12))

# Andar / Bahar
cols_frame = ctk.CTkFrame(board, fg_color="#041f1c", corner_radius=10)
cols_frame.grid(row=0, column=1, padx=12, pady=12)

andar_col = ctk.CTkFrame(cols_frame, fg_color="#042f2a", corner_radius=8)
andar_col.grid(row=0, column=0, padx=12)
ctk.CTkLabel(andar_col, text="ANDAR", font=("Arial Black", 18), text_color="#8ef0c6").pack(pady=(10, 6))
andar_img = ctk.CTkLabel(andar_col, text="", width=140, height=200, fg_color="#021a17")
andar_img.pack(padx=8, pady=8)

bahar_col = ctk.CTkFrame(cols_frame, fg_color="#04221f", corner_radius=8)
bahar_col.grid(row=0, column=1, padx=12)
ctk.CTkLabel(bahar_col, text="BAHAR", font=("Arial Black", 18), text_color="#ff9c9c").pack(pady=(10, 6))
bahar_img = ctk.CTkLabel(bahar_col, text="", width=140, height=200, fg_color="#021a17")
bahar_img.pack(padx=8, pady=8)

# Controls
controls = ctk.CTkFrame(root, fg_color="#041f1c", corner_radius=8)
controls.pack(fill="x", padx=16, pady=(8, 12))
status_label = ctk.CTkLabel(controls, text="Waiting for card reader...", font=("Arial", 12))
status_label.grid(row=0, column=0, padx=12, pady=10, sticky="w")
ctk.CTkButton(controls, text="New Round (/)", width=160, command=lambda: reset_game()).grid(row=0, column=1, padx=6)
ctk.CTkButton(controls, text="Manual Andar (1)", width=140, command=lambda: manual_result('ANDAR')).grid(row=0,
                                                                                                         column=2,
                                                                                                         padx=6)
ctk.CTkButton(controls, text="Manual Bahar (2)", width=140, command=lambda: manual_result('BAHAR')).grid(row=0,
                                                                                                         column=3,
                                                                                                         padx=6)

# Bead history
bead_frame = ctk.CTkFrame(root, fg_color="#021d18", corner_radius=8)
bead_frame.pack(fill="x", padx=16, pady=(0, 16))
ctk.CTkLabel(bead_frame, text="History (Bead-style)", font=("Arial", 12), text_color="#bfe8d6").pack(anchor='w', padx=8,
                                                                                                     pady=(8, 0))
bead_canvas = ctk.CTkCanvas(bead_frame, height=160, bg="#011814", highlightthickness=0)
bead_canvas.pack(padx=10, pady=8, fill='x')


# ------------------ Images ------------------
def load_ctk_image(card_name, target_w=140, target_h=200):
    img_path = os.path.join(CARDS_DIR, f"{card_name}.png")
    if not os.path.exists(img_path):
        return None
    img = Image.open(img_path).convert('RGBA')

    ratio = img.width / img.height
    if ratio > (target_w / target_h):
        new_w = target_w
        new_h = int(target_w / ratio)
    else:
        new_h = target_h
        new_w = int(target_h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    key = f"{card_name}_{new_w}x{new_h}"
    ctk_img = CTkImage(light_image=img, dark_image=img, size=(new_w, new_h))
    _image_cache[key] = ctk_img
    return ctk_img


# ------------------ Bead draw ------------------
def draw_bead_plate():
    bead_canvas.delete('all')
    cols = max(1, len(bead_columns))
    cell_w = 34
    cell_h = 34
    pad_x = 8
    pad_y = 12
    width = cols * (cell_w + 8) + pad_x * 2
    height = BEAD_ROWS * (cell_h + 6) + pad_y * 2
    bead_canvas.configure(width=min(width, 1200), height=height)

    for ci, col in enumerate(bead_columns):
        for ri in range(BEAD_ROWS):
            x = pad_x + ci * (cell_w + 8)
            y = pad_y + ri * (cell_h + 6)
            bead_canvas.create_rectangle(x, y, x + cell_w, y + cell_h,
                                         fill='#02221b', outline='#00160f')
            if ri < len(col):
                val = col[ri]
                fill = '#2bd6a6' if val == 'A' else '#ff6b6b'
                txt = 'A' if val == 'A' else 'B'
                txt_color = '#002218' if val == 'A' else '#3a0000'
                cx = x + cell_w // 2
                cy = y + cell_h // 2
                r = min(cell_w, cell_h) // 2 - 4
                bead_canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                        fill=fill, outline='#001614')
                bead_canvas.create_text(cx, cy, text=txt, fill=txt_color,
                                        font=('Consolas', 12, 'bold'))


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
def evaluate_for_match(card_name, side):
    global game_over, game_counter
    if game_over or not joker_card:
        return
    if card_rank(card_name) == card_rank(joker_card):
        game_over = True
        symbol = 'A' if side == 'ANDAR' else 'B'
        append_bead(symbol)
        show_popup(f"{side} WINS!")
        game_counter += 1
        game_label.configure(text=f"Game: {game_counter}")


def show_popup(text):
    global winner_popup
    if winner_popup and winner_popup.winfo_exists():
        try:
            winner_popup.destroy()
        except:
            pass
    winner_popup = ctk.CTkToplevel(root)
    winner_popup.overrideredirect(True)
    winner_popup.geometry('380x100')
    winner_popup.configure(fg_color='#00271f')
    lbl = ctk.CTkLabel(winner_popup, text=text, text_color='#ffd36e',
                       font=('Arial Black', 20))
    lbl.pack(expand=True)
    x = root.winfo_screenwidth() // 2 - 190
    y = root.winfo_screenheight() // 2 - 60
    winner_popup.geometry(f'380x100+{x}+{y}')
    root.after(1600, lambda: (winner_popup.destroy()
                              if winner_popup and winner_popup.winfo_exists() else None))


def reset_game():
    global joker_card, side_toggle, game_over
    joker_card = None
    side_toggle = True
    game_over = False
    joker_text.configure(text='Waiting...')
    joker_img.configure(image=None, text='')
    andar_img.configure(image=None, text='')
    bahar_img.configure(image=None, text='')
    status_label.configure(text='New round — waiting for Joker')


def manual_result(side):
    if game_over:
        return
    symbol = 'A' if side == 'ANDAR' else 'B'
    append_bead(symbol)
    show_popup(f"{side} WINS!")


# ------------------ SERIAL READER (FIXED) ------------------
def serial_reader():
    global joker_card, side_toggle, game_over
    buffer = ""

    while not stop_event.is_set():
        if not ser:
            time.sleep(1)
            continue
        try:
            data = ser.read(ser.in_waiting or 1).decode(errors="ignore")
            if not data:
                time.sleep(0.02)
                continue

            buffer += data

            while len(buffer) >= 2:
                chunk = buffer[:4].strip()
                buffer = buffer[4:]

                print("[DEBUG] Chunk:", repr(chunk))

                if chunk in card_map:
                    card_name = card_map[chunk]
                    root.after(0, status_label.configure, {"text": f"Card detected: {card_name}"})

                    if not joker_card:
                        joker_card = card_name
                        img = load_ctk_image(card_name, 160, 220)
                        root.after(0, joker_text.configure, {"text": f"Joker: {card_name}"})
                        root.after(0, joker_img.configure, {"image": img, "text": ""})
                        joker_img.image = img

                    else:
                        side = "ANDAR" if side_toggle else "BAHAR"
                        target = andar_img if side_toggle else bahar_img

                        img = load_ctk_image(card_name)
                        root.after(0, target.configure, {"image": img, "text": ""})
                        target.image = img

                        root.after(0, evaluate_for_match, card_name, side)
                        side_toggle = not side_toggle

        except Exception as e:
            print("Serial Read Error:", e)
            time.sleep(0.1)

        time.sleep(0.01)


# ------------------ Exit ------------------
def on_close():
    stop_event.set()
    try:
        if ser and ser.is_open:
            ser.close()
    except:
        pass
    try:
        root.destroy()
    except:
        pass


root.protocol("WM_DELETE_WINDOW", on_close)

# ------------------ Keybinds ------------------
root.bind('/', lambda e: reset_game())
root.bind('1', lambda e: manual_result('ANDAR'))
root.bind('2', lambda e: manual_result('BAHAR'))

# Start thread
threading.Thread(target=serial_reader, daemon=True).start()

draw_bead_plate()

root.mainloop()
