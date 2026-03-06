"""
Shortcut para levantar el servidor en desarrollo.
Uso: python run_server.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["server", "landing"],
    )
