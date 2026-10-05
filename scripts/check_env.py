"""
Environment and Hardware Pre-flight Check for Topic T7 (TV1 - Windows 11 Support)
Target Device: Laptop HP Victus 16 (Windows 11)
"""

import sys
import os
import platform
import multiprocessing

def check_system():
    print("=" * 60)
    print("Pre-flight Environment Check: Topic T7 Multi-Camera Profiling")
    print("=" * 60)
    
    # 1. OS & Python
    os_name = platform.system()
    os_release = platform.release()
    os_ver = platform.version()
    py_ver = sys.version.split()[0]
    
    print(f"[OS] System: {os_name} {os_release} (Version: {os_ver})")
    print(f"[Python] Version: {py_ver}")
    
    if sys.version_info < (3, 8):
        print("  [!] WARNING: Python version >= 3.8 is required for multiprocessing.shared_memory.")
    else:
        print("  [OK] Python version is compatible.")

    # 2. CPU & Memory
    cpu_count = os.cpu_count() or 1
    print(f"[Hardware] CPU Logical Cores: {cpu_count}")
    
    try:
        import psutil
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        avail_gb = mem.available / (1024 ** 3)
        print(f"[Hardware] Total RAM: {total_gb:.2f} GB | Available: {avail_gb:.2f} GB")
        if avail_gb < 2.0:
            print("  [!] WARNING: Less than 2 GB RAM available. Might impact multi-camera synthetic buffers.")
        else:
            print("  [OK] RAM capacity is adequate for synthetic RGB-D buffers.")
    except ImportError:
        print("[Hardware] psutil is not installed. Run: pip install -r requirements.txt")

    # 3. Check multiprocessing spawn mechanism (Windows default)
    mp_context = multiprocessing.get_start_method(allow_none=True)
    print(f"[IPC] Multiprocessing start method: {mp_context}")
    if os_name == "Windows" and mp_context != "spawn":
        print("  [NOTE] Windows should enforce 'spawn' mode for worker processes.")

    # 4. Check shared_memory module
    try:
        from multiprocessing import shared_memory
        shm_test = shared_memory.SharedMemory(create=True, size=1024, name="t7_env_test_shm")
        shm_test.close()
        shm_test.unlink()
        print("  [OK] multiprocessing.shared_memory is functional on this OS.")
    except Exception as e:
        print(f"  [!] Shared memory test failed: {e}")

    # 5. Required Libraries Check
    libraries = ["numpy", "pandas", "matplotlib", "psutil"]
    print("-" * 60)
    print("Checking Required Libraries:")
    missing = []
    for lib in libraries:
        try:
            mod = __import__(lib)
            ver = getattr(mod, "__version__", "unknown")
            print(f"  - {lib}: INSTALLED (v{ver})")
        except ImportError:
            print(f"  - {lib}: MISSING")
            missing.append(lib)

    print("=" * 60)
    if missing:
        print(f"ACTION REQUIRED: Please install missing packages using:")
        print(f"  pip install -r requirements.txt")
        return False
    else:
        print("STATUS: All core environment components are READY for integration.")
        return True

if __name__ == "__main__":
    check_system()

