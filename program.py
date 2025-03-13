import tkinter as tk
from tkinter import filedialog, messagebox
import os
import random
import pickle

class MIPS_CPU:
    def __init__(self):
        self.regs = [0] * 33  # 32 GPRs + PC (regs[32])
        self.regs[32] = 0xBFC00000  # N64 reset vector
        self.memory = bytearray(4 * 1024 * 1024)  # 4MB RDRAM
        self.cycles = 0

    def read_word(self, addr):
        addr -= 0x80000000  # Map to RDRAM
        if 0 <= addr < len(self.memory) - 3:
            return int.from_bytes(self.memory[addr:addr+4], 'big')
        return 0

    def write_word(self, addr, value):
        addr -= 0x80000000
        if 0 <= addr < len(self.memory) - 3:
            self.memory[addr:addr+4] = value.to_bytes(4, 'big')

    def step(self):
        pc = self.regs[32]
        instr = self.read_word(pc)
        opcode = (instr >> 26) & 0x3F
        if opcode == 0x08:  # ADDI
            rt = (instr >> 16) & 0x1F
            rs = (instr >> 21) & 0x1F
            imm = instr & 0xFFFF
            if imm & 0x8000:  # Sign-extend
                imm -= 0x10000
            self.regs[rt] = (self.regs[rs] + imm) & 0xFFFFFFFF
        elif opcode == 0x23:  # LW
            rt = (instr >> 16) & 0x1F
            rs = (instr >> 21) & 0x1F
            imm = instr & 0xFFFF
            if imm & 0x8000:
                imm -= 0x10000
            addr = (self.regs[rs] + imm) & 0xFFFFFFFF
            self.regs[rt] = self.read_word(addr)
        elif opcode == 0x00:  # SPECIAL
            funct = instr & 0x3F
            if funct == 0x20:  # ADD
                rd = (instr >> 11) & 0x1F
                rs = (instr >> 21) & 0x1F
                rt = (instr >> 16) & 0x1F
                self.regs[rd] = (self.regs[rs] + self.regs[rt]) & 0xFFFFFFFF
        self.regs[32] = (pc + 4) & 0xFFFFFFFF
        self.cycles += 1

class N64Emulator:
    def __init__(self):
        self.cpu = MIPS_CPU()
        self.rom = None
        self.running = False
        self.paused = False
        self.plugins = {
            "Personalizer": True,  # Always on for SM64
            "Rediscovered": False,
            "Wonder Graphics": False,
            "Debugger": False
        }
        self.cheats = {"Infinite Health": False}
        self.mario_hat_color = "Red"  # Personalization demo

    def load_rom(self, path):
        with open(path, "rb") as f:
            self.rom = f.read()
        # Simulate PI DMA: Copy first 0x1000 bytes to 0x80000000
        self.cpu.memory[0:0x1000] = self.rom[0:0x1000]
        self.cpu.regs[32] = 0x80000000  # Jump to RAM after boot

    def reset(self):
        self.cpu = MIPS_CPU()
        if self.rom:
            self.cpu.memory[0:0x1000] = self.rom[0:0x1000]
        self.running = True

    def step(self):
        if not self.running or self.paused:
            return
        self.cpu.step()
        # Personalization AI: Randomize Mario's hat color every 1000 cycles
        if self.plugins["Personalizer"] and self.cpu.cycles % 1000 == 0:
            self.mario_hat_color = random.choice(["Red", "Blue", "Green"])
        # Rediscovered: Hypothetical unused coin at cycle 5000
        if self.plugins["Rediscovered"] and self.cpu.cycles == 5000:
            self.cpu.write_word(0x80300000, 1)  # Fake coin spawn
        # Cheat: Infinite Health (placeholder address)
        if self.cheats["Infinite Health"]:
            self.cpu.write_word(0x8033B21E, 8)  # SM64 health address

    def save_state(self, path):
        with open(path, "wb") as f:
            pickle.dump((self.cpu.regs, self.cpu.memory, self.mario_hat_color), f)

    def load_state(self, path):
        with open(path, "rb") as f:
            self.cpu.regs, self.cpu.memory, self.mario_hat_color = pickle.load(f)

class EmulatorGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Grok 3 N64 Emulator")
        self.master.geometry("600x400")
        self.emu = N64Emulator()
        self.setup_ui()
        self.update_frame()

    def setup_ui(self):
        # Menu Bar
        menubar = tk.Menu(self.master)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open ROM...", command=self.open_rom)
        filemenu.add_command(label="Reset", command=self.reset)
        filemenu.add_command(label="Exit", command=self.master.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        pluginmenu = tk.Menu(menubar, tearoff=0)
        for plugin in self.emu.plugins:
            pluginmenu.add_checkbutton(label=plugin, onvalue=True, offvalue=False,
                                       variable=tk.BooleanVar(value=self.emu.plugins[plugin]),
                                       command=lambda p=plugin: self.toggle_plugin(p))
        menubar.add_cascade(label="Plugins", menu=pluginmenu)

        cheatmenu = tk.Menu(menubar, tearoff=0)
        for cheat in self.emu.cheats:
            cheatmenu.add_checkbutton(label=cheat, onvalue=True, offvalue=False,
                                      variable=tk.BooleanVar(value=self.emu.cheats[cheat]),
                                      command=lambda c=cheat: self.toggle_cheat(c))
        menubar.add_cascade(label="Cheats", menu=cheatmenu)

        self.master.config(menu=menubar)

        # ROM Catalog
        self.catalog_frame = tk.Frame(self.master)
        self.catalog_list = tk.Listbox(self.catalog_frame, height=10)
        self.catalog_list.pack(fill=tk.BOTH, expand=True)
        self.catalog_list.insert(tk.END, "Super Mario 64 (Built-in)")
        self.catalog_frame.pack(fill=tk.BOTH, expand=True)

        # Display Area
        self.display = tk.Label(self.master, text="No ROM Loaded", bg="black", fg="white",
                                width=60, height=15, anchor="nw", justify="left")
        self.display.pack()

        # Controls
        control_frame = tk.Frame(self.master)
        tk.Button(control_frame, text="Play/Pause", command=self.toggle_pause).pack(side=tk.LEFT)
        tk.Button(control_frame, text="Save State", command=self.save_state).pack(side=tk.LEFT)
        tk.Button(control_frame, text="Load State", command=self.load_state).pack(side=tk.LEFT)
        control_frame.pack()

    def toggle_plugin(self, plugin):
        self.emu.plugins[plugin] = not self.emu.plugins[plugin]
        if plugin == "Debugger" and self.emu.plugins[plugin]:
            self.show_debugger()

    def toggle_cheat(self, cheat):
        self.emu.cheats[cheat] = not self.emu.cheats[cheat]

    def open_rom(self):
        path = filedialog.askopenfilename(filetypes=[("N64 ROMs", "*.z64 *.n64")])
        if path:
            self.emu.load_rom(path)
            self.emu.reset()
            self.display.config(text="ROM Loaded: Running...")

    def reset(self):
        self.emu.reset()
        self.display.config(text="ROM Reset: Running...")

    def toggle_pause(self):
        self.emu.paused = not self.emu.paused
        self.display.config(text=f"{'Paused' if self.emu.paused else 'Running'}")

    def save_state(self):
        path = filedialog.asksaveasfilename(defaultextension=".sav")
        if path:
            self.emu.save_state(path)

    def load_state(self):
        path = filedialog.askopenfilename(filetypes=[("Save States", "*.sav")])
        if path:
            self.emu.load_state(path)

    def show_debugger(self):
        debug_win = tk.Toplevel(self.master)
        debug_win.title("Debugger")
        tk.Label(debug_win, text=f"PC: {hex(self.emu.cpu.regs[32])}").pack()
        tk.Label(debug_win, text=f"Cycles: {self.emu.cpu.cycles}").pack()
        mem_view = tk.Text(debug_win, height=10, width=50)
        mem_str = "\n".join(f"{hex(addr)}: {hex(self.emu.cpu.read_word(addr))}"
                           for addr in range(0x80000000, 0x80000100, 4))
        mem_view.insert(tk.END, mem_str)
        mem_view.pack()

    def update_frame(self):
        if self.emu.running:
            self.emu.step()
            status = f"Running - Cycles: {self.emu.cpu.cycles}\n"
            status += f"Personalization: Mario's Hat = {self.emu.mario_hat_color}\n"
            if self.emu.plugins["Rediscovered"]:
                status += "Rediscovered: Unused Coin Spawned\n"
            if self.emu.plugins["Wonder Graphics"]:
                status += "Wonder Graphics: Enhanced (Placeholder)\n"
            self.display.config(text=status)
        self.master.after(16, self.update_frame)  # ~60 FPS

if __name__ == "__main__":
    root = tk.Tk()
    app = EmulatorGUI(root)
    root.mainloop()
