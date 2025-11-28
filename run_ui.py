"""
Quick start script for Multitenant Streamlit UI
"""
import subprocess
import sys
import os

def main():
    """Run the Streamlit UI."""
    print("🚀 Starting Multitenant RAG System UI...")
    print("=" * 60)
    print("📍 Backend should be running on: http://127.0.0.1:8000")
    print("🌐 UI will be available at: http://localhost:8501")
    print("=" * 60)
    print("\n💡 Demo Login: Use 'default-tenant' as Tenant ID\n")
    
    # Set environment variable if not set
    if "BACKEND_URL" not in os.environ:
        os.environ["BACKEND_URL"] = "http://127.0.0.1:8000/api/v1"
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "ui/app_multitenant.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down UI...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure streamlit is installed: pip install streamlit")

if __name__ == "__main__":
    main()
