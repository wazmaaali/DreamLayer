import requests
import logging

logger = logging.getLogger(__name__)

COMFY_API_URL = "http://127.0.0.1:8188"

def interrupt_workflow():
    """
    Interrupt a currently running workflow in ComfyUI
    """
    try:
        response = requests.post(f"{COMFY_API_URL}/interrupt")
        if response.status_code == 200:
            logger.info("Successfully sent interrupt signal to ComfyUI")
            return True
        else:
            logger.error(f"Failed to interrupt workflow: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error interrupting workflow: {str(e)}")
        return False 