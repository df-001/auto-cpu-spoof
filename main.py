import ctypes
import sys
import os
import winreg
import json

# resolve config path relative to the executable
_BASE_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
CONFIG_FILE = os.path.join(_BASE_DIR, "cpu_spoof_cfg.json")
REG_RUN_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
REG_CPU_PATH = r"HARDWARE\DESCRIPTION\System\CentralProcessor"
PROCESS_NAME = "AutoCPUSpoofer"

def is_admin():
    return ctypes.windll.shell32.IsUserAnAdmin()

def run_as_admin():
    args = " ".join(sys.argv[1:])  # forwards arguments to the elevated process
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, None, 1)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"cpu_name": "", "startup": False}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
    print("[SUCCESS]: Saved config file.")

def manage_startup(action):
    """
    Adds or removes the executable from startup via Windows Run registry.
    
    NOTE: Function assumes program is compiled to .exe
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE)
        
        if action == "add":
            # creates and sets new startup rule
            command = f'"{sys.executable}" --silent'
            
            winreg.SetValueEx(key, PROCESS_NAME, 0, winreg.REG_SZ, command)

            config["startup"] = True
            print("[SUCCESS]: Added to Windows startup.")
            save_config(config)
            
        elif action == "remove":
            try:
                winreg.DeleteValue(key, PROCESS_NAME)

                config["startup"] = False
                print("[SUCCESS]: Removed from Windows startup.")
                save_config(config)
            except FileNotFoundError:
                config["startup"] = False
                print("[ERROR]: Application was not found in startup registry.")
                
        winreg.CloseKey(key)
    except PermissionError:
        print("[ERROR]: Administrator privileges not granted.")
    except Exception as e:
        print(f"[ERROR] Startup management failed: {e}")


def get_thread_count():
    """ Gets number of subkeys in CPU desc registry. """
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_CPU_PATH, 0, winreg.KEY_READ) as key:
            # winreg.QueryInfoKey returns tuple (num_subkeys, num_values, last_modified)
            info = winreg.QueryInfoKey(key)
            return info[0]
    except WindowsError as e:
        return None

def apply_patch(name):
    """Applies custom name patch to each CPU thread."""

    try:
        cpu_root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_CPU_PATH)
        
        # iterate through each thread
        thread_count = get_thread_count()
        if thread_count is None:
            raise Exception("Failed to retrieve thread count.")

        for i in range(thread_count):
            print(f"[OPERATION]: Applying patch on thread ({i})")
            thread_name = winreg.EnumKey(cpu_root, i)
            thread_key_path = f"{REG_CPU_PATH}\\{thread_name}"
            thread_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, thread_key_path, 0, winreg.KEY_SET_VALUE)

            winreg.SetValueEx(thread_key, "ProcessorNameString", 0, winreg.REG_SZ, name)
            winreg.CloseKey(thread_key)
        winreg.CloseKey(cpu_root)
        
        print(f"[SUCCESS]: Applied patch on ({thread_count+1}) threads.")

        config["cpu_name"] = name
        save_config(config)

    except Exception as e:
        print(f"[ERROR] Failed to apply registry spoof: {e}")

config = load_config()

def main():
    if not is_admin():
        print("[ACTION] Requesting Administrator privileges")
        run_as_admin()
        sys.exit()

    # silent launch for start up
    if len(sys.argv) > 1 and sys.argv[1] == "--silent":
        if config.get("startup") and config.get("cpu_name"):
            apply_patch(config["cpu_name"])
        sys.exit()

    # Main CLI program

    while True:
        os.system("cls")

        print("\ndf-001 Auto CPU Spoofer")
        print(f"\nCPU Name: {config['cpu_name'] if config['cpu_name'] else 'None'}")
        print(f"Apply on startup: {'[Enabled at boot]' if config['startup'] else '[Disabled]'}")
        print("\nOptions:")
        print("[1]. Set CPU name")
        print("[2]. Enable Startup")
        print("[3]. Disable Startup")
        print("[4]. Exit")

        choice = input()

        if choice == "1":
            name = input("Enter custom name:\n")
            apply_patch(name)
            input("Continue:")
        elif choice == "2":
            manage_startup("add")
            input("Continue:")
        elif choice == "3":
            manage_startup("remove")
            input("Continue:")
        elif choice == "4":
            sys.exit()
        else:
            print("[ERROR]: Invalid selection.")
            input("Continue:")

if __name__ == "__main__":
    main()