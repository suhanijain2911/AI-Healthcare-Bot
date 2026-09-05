
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib
import threading
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3.6-flash")

BG = "#eaf6f6"
PRIMARY = "#1e3a8a"
ACCENT = "#16a34a"
DANGER = "#dc2626"
FONT = "Segoe UI"

EMERGENCY_WORDS = [
    "chest pain", "difficulty breathing", "shortness of breath",
    "can't breathe", "cannot breathe", "severe bleeding",
    "unconscious", "seizure", "stroke", "heart attack",
]

SYMPTOMS = [
    "Headache", "Fever", "Cough", "Stomach Pain", "Back Pain",
    "Cold", "Allergy", "Eye Pain", "Toothache", "Fatigue",
]


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = sqlite3.connect("users.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
    conn.commit()
    conn.close()


def create_user(username, password):
    conn = sqlite3.connect("users.db")
    try:
        conn.execute("INSERT INTO users VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def check_user(username, password):
    conn = sqlite3.connect("users.db")
    row = conn.execute("SELECT password FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return row is not None and row[0] == hash_password(password)


def is_emergency(problems):
    text = " ".join(problems).lower()
    return any(word in text for word in EMERGENCY_WORDS)


def ask_gemini(name, age, gender, problems):
    prompt = f"""
You are an AI health assistant, not a real doctor.
Patient: {name}, Age {age}, Gender {gender}
Symptoms: {problems}

Give 4-6 short bullet points of safe general self-care advice.
Do not diagnose. Do not suggest strong or prescription medicines.
End with a line recommending a real doctor visit.
Keep the whole response under 120 words so it loads fast.
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Could not connect to AI service.\nError: {e}"


class HealthApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Healthcare Bot")
        self.geometry("900x700")
        self.configure(bg=BG)

        self.patient = {}
        self.problems = []

        self.frame = tk.Frame(self, bg=BG)
        self.frame.pack(fill="both", expand=True)

        self.show_home()

    def clear(self):
        for w in self.frame.winfo_children():
            w.destroy()

    def show_home(self):
        self.clear()
        tk.Label(self.frame, text="AI Healthcare Bot", font=(FONT, 30, "bold"),
                 bg=BG, fg=PRIMARY).pack(pady=(80, 10))
        tk.Label(self.frame, text="Your AI-powered health assistant", font=(FONT, 13),
                 bg=BG, fg="gray30").pack(pady=(0, 40))

        ttk.Button(self.frame, text="Login", command=self.show_login).pack(pady=8, ipadx=20, ipady=5)
        ttk.Button(self.frame, text="Sign Up", command=self.show_signup).pack(pady=8, ipadx=20, ipady=5)

    def show_signup(self):
        self.clear()
        tk.Label(self.frame, text="Create Account", font=(FONT, 22, "bold"), bg=BG, fg=PRIMARY).pack(pady=30)

        tk.Label(self.frame, text="Username", bg=BG).pack()
        username = ttk.Entry(self.frame, width=30)
        username.pack(pady=5)

        tk.Label(self.frame, text="Password", bg=BG).pack()
        password = ttk.Entry(self.frame, width=30, show="*")
        password.pack(pady=5)

        def submit():
            if not username.get() or not password.get():
                messagebox.showwarning("Error", "Fill all fields")
                return
            if create_user(username.get(), password.get()):
                messagebox.showinfo("Success", "Account created, please login")
                self.show_login()
            else:
                messagebox.showerror("Error", "Username already exists")

        ttk.Button(self.frame, text="Sign Up", command=submit).pack(pady=15)
        ttk.Button(self.frame, text="Back", command=self.show_home).pack()

    def show_login(self):
        self.clear()
        tk.Label(self.frame, text="Login", font=(FONT, 22, "bold"), bg=BG, fg=PRIMARY).pack(pady=30)

        tk.Label(self.frame, text="Username", bg=BG).pack()
        username = ttk.Entry(self.frame, width=30)
        username.pack(pady=5)

        tk.Label(self.frame, text="Password", bg=BG).pack()
        password = ttk.Entry(self.frame, width=30, show="*")
        password.pack(pady=5)

        def submit():
            if check_user(username.get(), password.get()):
                self.show_details()
            else:
                messagebox.showerror("Error", "Invalid username or password")

        ttk.Button(self.frame, text="Login", command=submit).pack(pady=15)
        ttk.Button(self.frame, text="Back", command=self.show_home).pack()

    def show_details(self):
        self.clear()
        tk.Label(self.frame, text="Patient Details", font=(FONT, 22, "bold"), bg=BG, fg=PRIMARY).pack(pady=20)

        form = tk.Frame(self.frame, bg=BG)
        form.pack()

        fields = ["Full Name", "Age", "Gender", "Phone", "Email", "Address", "Blood Group"]
        entries = {}
        for i, f in enumerate(fields):
            tk.Label(form, text=f, bg=BG).grid(row=i, column=0, sticky="w", pady=6, padx=5)
            entry = ttk.Entry(form, width=30)
            entry.grid(row=i, column=1, pady=6)
            entries[f] = entry

        def submit():
            name = entries["Full Name"].get()
            age = entries["Age"].get()
            if not name or not age.isdigit():
                messagebox.showwarning("Error", "Enter valid name and age")
                return
            self.patient = {f: entries[f].get() for f in fields}
            self.show_symptoms()

        ttk.Button(self.frame, text="Next", command=submit).pack(pady=15)
        ttk.Button(self.frame, text="Back", command=self.show_login).pack()

    def show_symptoms(self):
        self.clear()
        tk.Label(self.frame, text="Select Symptoms", font=(FONT, 22, "bold"), bg=BG, fg=PRIMARY).pack(pady=20)

        grid = tk.Frame(self.frame, bg=BG)
        grid.pack()

        checks = {}
        for i, s in enumerate(SYMPTOMS):
            var = tk.BooleanVar()
            tk.Checkbutton(grid, text=s, variable=var, bg=BG, font=(FONT, 12)) \
                .grid(row=i // 2, column=i % 2, sticky="w", padx=20, pady=4)
            checks[s] = var

        tk.Label(self.frame, text="Other (comma separated)", bg=BG).pack(pady=(20, 5))
        other = ttk.Entry(self.frame, width=50)
        other.pack()

        def submit():
            chosen = [s for s, v in checks.items() if v.get()]
            if other.get().strip():
                chosen += [x.strip() for x in other.get().split(",") if x.strip()]
            if not chosen:
                messagebox.showwarning("Error", "Select at least one symptom")
                return
            self.problems = chosen
            self.show_result()

        ttk.Button(self.frame, text="Get Guidance", command=submit).pack(pady=20)
        ttk.Button(self.frame, text="Back", command=self.show_details).pack()

    def show_result(self):
        self.clear()

        if is_emergency(self.problems):
            tk.Label(self.frame, text="Emergency Warning", font=(FONT, 22, "bold"),
                     bg=BG, fg=DANGER).pack(pady=40)
            tk.Label(self.frame, text="This looks serious. Please call emergency services\n"
                                       "or visit the nearest hospital immediately.",
                     font=(FONT, 14), bg=BG, fg=DANGER, justify="center").pack(pady=10)
            ttk.Button(self.frame, text="Back to Home", command=self.show_home).pack(pady=30)
            return

        # Receipt-style white box
        box_frame = tk.Frame(self.frame, bg="white", bd=3, relief="solid")
        box_frame.pack(pady=30, padx=150, fill="both", expand=True)

        tk.Label(box_frame, text="\U0001F4CB Medical Receipt", font=("Arial", 22, "bold"),
                 bg="white").pack(pady=15)
        tk.Frame(box_frame, height=2, bg=PRIMARY).pack(fill="x", padx=10, pady=5)

        tk.Label(box_frame, text="Information", font=("Arial", 16, "bold"),
                 bg="white", anchor="w").pack(pady=5, anchor="w", padx=15)

        info_text = (
            f"\U0001F464 Full Name: {self.patient.get('Full Name', '')}\n"
            f"\U0001F4C5 Age: {self.patient.get('Age', '')}\n"
            f"\u26A5 Gender: {self.patient.get('Gender', '')}\n"
            f"\U0001F4DE Phone: {self.patient.get('Phone', '')}\n"
            f"\U0001F4E7 Email: {self.patient.get('Email', '')}\n"
            f"\U0001F3E0 Address: {self.patient.get('Address', '')}\n"
            f"\U0001FA78 Blood Group: {self.patient.get('Blood Group', '')}\n"
            f"\U0001FA7A Problems: {', '.join(self.problems)}"
        )
        tk.Label(box_frame, text=info_text, font=("Arial", 12), bg="white",
                 justify="left", anchor="w").pack(pady=5, padx=15, anchor="w")

        tk.Frame(box_frame, height=2, bg=PRIMARY).pack(fill="x", padx=10, pady=5)
        tk.Label(box_frame, text="\U0001F48A Prescription", font=("Arial", 16, "bold"),
                 bg="white", anchor="w").pack(pady=5, anchor="w", padx=15)

        loading = tk.Label(box_frame, text="Getting AI response, please wait a few seconds...",
                            bg="white", font=("Arial", 11, "italic"), fg="gray30")
        loading.pack(pady=10)

        text_frame = tk.Frame(box_frame, bg="white")
        text_frame.pack(padx=15, pady=10, fill="both", expand=True)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        box = tk.Text(text_frame, font=("Arial", 12), wrap="word",
                       bg="white", relief="flat", yscrollcommand=scrollbar.set)
        box.pack(fill="both", expand=True)
        scrollbar.config(command=box.yview)
        box.config(state="disabled")

        def worker():
            text = ask_gemini(
                self.patient.get("Full Name", ""), self.patient.get("Age", ""),
                self.patient.get("Gender", ""), ", ".join(self.problems)
            )
            self.after(0, lambda: fill_result(text))

        def fill_result(text):
            loading.destroy()
            text = text.replace("**", "").replace("* ", "- ")
            box.config(state="normal")
            box.insert("1.0", text)
            box.config(state="disabled")

        threading.Thread(target=worker, daemon=True).start()

        tk.Label(box_frame, text="\u2714 Generated by AI Healthcare Bot | For guidance only, not a medical diagnosis.",
                 font=("Arial", 10, "italic"), fg="gray30", bg="white").pack(pady=10)

        ttk.Button(self.frame, text="Back to Home", command=self.show_home).pack(pady=15)


if __name__ == "__main__":
    init_db()
    app = HealthApp()
    app.mainloop()
