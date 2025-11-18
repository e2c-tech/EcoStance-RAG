import subprocess
import sys
import time

def main():
    """
    Launches both the FastAPI backend and the Streamlit UI as separate processes.
    Monitors the processes and ensures they are terminated when the script is stopped.
    """
    # Command to run the FastAPI backend using uvicorn
    backend_command = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000"
        # Note: --reload is omitted as it can cause issues with subprocess management.
        # For development, it's often better to run the backend separately with --reload.
    ]

    # Command to run the Streamlit UI
    frontend_command = [
        sys.executable, "-m", "streamlit", "run",
        "ui/app.py",
        "--server.port", "8501"
    ]

    backend_proc = None
    frontend_proc = None

    try:
        print("--- Starting FastAPI backend... ---")
        # Launch the backend process
        backend_proc = subprocess.Popen(backend_command, stdout=sys.stdout, stderr=sys.stderr)
        print(f"Backend process started with PID: {backend_proc.pid}")

        # Give the backend a moment to start up
        time.sleep(5)

        print("\n--- Starting Streamlit frontend... ---")
        # Launch the frontend process
        frontend_proc = subprocess.Popen(frontend_command, stdout=sys.stdout, stderr=sys.stderr)
        print(f"Frontend process started with PID: {frontend_proc.pid}")
        
        print("\n--- Both applications are running. ---")
        print("Backend (API) is at: http://127.0.0.1:8000")
        print("Frontend (UI) is at: http://127.0.0.1:8501")
        print("\nPress Ctrl+C to stop both applications.")

        # Wait for the frontend process to terminate. If the user closes the Streamlit
        # window or stops the script, this will allow the finally block to execute.
        frontend_proc.wait()

    except KeyboardInterrupt:
        print("\n--- Ctrl+C received. Shutting down applications... ---")
    finally:
        # Terminate the processes in reverse order of startup
        if frontend_proc and frontend_proc.poll() is None:
            print("Stopping Streamlit frontend...")
            frontend_proc.terminate()
            frontend_proc.wait()
        
        if backend_proc and backend_proc.poll() is None:
            print("Stopping FastAPI backend...")
            backend_proc.terminate()
            backend_proc.wait()
        
        print("--- All applications have been shut down. ---")

if __name__ == "__main__":
    main()
