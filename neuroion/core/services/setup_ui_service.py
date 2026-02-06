# neuroion/core/services/setup_ui_service.py
"""
Service to automatically start the Setup UI when Core starts.
"""
import logging
import subprocess
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_setup_ui_process: Optional[subprocess.Popen] = None


def start_setup_ui() -> Optional[subprocess.Popen]:
    """
    Start the Setup UI development server.
    
    Returns the subprocess.Popen object if started successfully, None otherwise.
    """
    global _setup_ui_process
    
    if _setup_ui_process is not None:
        logger.info("Setup UI already running")
        return _setup_ui_process
    
    try:
        # Get project root (assuming this file is in neuroion/core/services/)
        project_root = Path(__file__).parent.parent.parent.parent
        setup_ui_dir = project_root / "setup-ui"
        
        if not setup_ui_dir.exists():
            logger.warning(f"Setup UI directory not found: {setup_ui_dir}")
            return None
        
        # Check if node_modules exists (dependencies installed)
        node_modules = setup_ui_dir / "node_modules"
        if not node_modules.exists():
            logger.warning("Setup UI dependencies not installed. Run 'npm install' in setup-ui/")
            return None
        
        # Start the dev server
        logger.info("Starting Setup UI...")
        _setup_ui_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(setup_ui_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "VITE_API_URL": "http://localhost:8000"},
        )
        
        logger.info("✅ Setup UI started successfully")
        return _setup_ui_process
        
    except Exception as e:
        logger.error(f"Failed to start Setup UI: {e}", exc_info=True)
        return None


def stop_setup_ui() -> None:
    """Stop the Setup UI process."""
    global _setup_ui_process
    
    if _setup_ui_process is not None:
        logger.info("Stopping Setup UI...")
        try:
            _setup_ui_process.terminate()
            _setup_ui_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _setup_ui_process.kill()
        except Exception as e:
            logger.error(f"Error stopping Setup UI: {e}")
        finally:
            _setup_ui_process = None
            logger.info("Setup UI stopped")