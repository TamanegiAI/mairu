#!/usr/bin/env python3
"""
Main entry point for the Google Docs Automation application.
This script provides commands to run either the FastAPI backend,
the Streamlit frontend, or both together.
"""

import argparse
import subprocess
import os
import sys
import threading
import time
import signal
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mairu")

def run_backend(port=8000):
    """Run the FastAPI backend server."""
    logger.info(f"Starting FastAPI backend on port {port}...")
    cmd = [sys.executable, "-m", "uvicorn", "src.app.main:app", "--reload", "--host", "0.0.0.0", "--port", str(port)]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    
    # Print output in real-time
    def log_output(pipe, prefix):
        for line in pipe:
            logger.info(f"{prefix}: {line.strip()}")
    
    # Start threads to monitor output
    threading.Thread(target=log_output, args=(process.stdout, "BACKEND"), daemon=True).start()
    threading.Thread(target=log_output, args=(process.stderr, "BACKEND ERROR"), daemon=True).start()
    
    return process

def run_frontend(port=8501):
    """Run the Streamlit frontend."""
    logger.info(f"Starting Streamlit frontend on port {port}...")
    cmd = [sys.executable, "-m", "streamlit", "run", "src/app/frontend/app.py", "--server.port", str(port)]
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    
    # Print output in real-time
    def log_output(pipe, prefix):
        for line in pipe:
            logger.info(f"{prefix}: {line.strip()}")
    
    # Start threads to monitor output
    threading.Thread(target=log_output, args=(process.stdout, "FRONTEND"), daemon=True).start()
    threading.Thread(target=log_output, args=(process.stderr, "FRONTEND ERROR"), daemon=True).start()
    
    return process

def run_both(backend_port=8000, frontend_port=8501):
    """Run both backend and frontend."""
    backend_process = run_backend(backend_port)
    # Wait a bit for backend to start
    time.sleep(2)
    frontend_process = run_frontend(frontend_port)
    
    return backend_process, frontend_process

def shutdown_processes(processes):
    """Gracefully shut down processes."""
    for process in processes:
        if process and process.poll() is None:  # If process is still running
            logger.info(f"Stopping process {process.pid}...")
            process.terminate()
            try:
                # Wait for process to terminate gracefully
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate within timeout
                logger.warning(f"Process {process.pid} did not terminate gracefully, force killing...")
                process.kill()

def main():
    """Parse arguments and run the appropriate server(s)."""
    parser = argparse.ArgumentParser(description="Run Google Docs Automation application")
    parser.add_argument("--backend-only", action="store_true", help="Run only the FastAPI backend")
    parser.add_argument("--frontend-only", action="store_true", help="Run only the Streamlit frontend")
    parser.add_argument("--backend-port", type=int, default=8000, help="Port for the backend server")
    parser.add_argument("--frontend-port", type=int, default=8501, help="Port for the frontend server")
    
    args = parser.parse_args()
    processes = []
    
    try:
        if args.backend_only:
            processes.append(run_backend(args.backend_port))
        elif args.frontend_only:
            processes.append(run_frontend(args.frontend_port))
        else:
            # Default: run both
            backend_proc, frontend_proc = run_both(args.backend_port, args.frontend_port)
            processes.extend([backend_proc, frontend_proc])
        
        # Setup handler for graceful shutdown
        def signal_handler(sig, frame):
            logger.info("Shutting down servers...")
            shutdown_processes(processes)
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Press Ctrl+C to stop the server(s)")
        
        # Keep main thread alive
        while all(p.poll() is None for p in processes):
            time.sleep(1)
            
        # If we get here, at least one process has terminated
        logger.warning("One or more processes terminated unexpectedly")
        shutdown_processes(processes)
        
    except Exception as e:
        logger.exception(f"Error while running servers: {e}")
        shutdown_processes(processes)
        sys.exit(1)

if __name__ == "__main__":
    main()