from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import base64
import json
import logging
import os
import sys
from PIL import Image
import io
import re
import random
import time
import requests
import shutil
import copy
from dream_layer import get_directories
from dream_layer_backend_utils.update_custom_workflow import update_custom_workflow, validate_custom_workflow, find_save_node, override_workflow, update_image_paths_in_workflow 
from dream_layer_backend_utils.api_key_injector import inject_api_keys_into_workflow
from dream_layer_backend_utils.workflow_loader import load_workflow, analyze_workflow
from shared_utils import wait_for_image, send_to_comfyui, serve_image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Configure CORS to allow requests from frontend
CORS(app, resources={
    r"/*": {  # Allow CORS for all routes
        "origins": ["http://localhost:8080"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

COMFY_API_URL = "http://127.0.0.1:8188"

# Get the absolute path to the ComfyUI root directory (parent of our backend directory)
COMFY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ComfyUI's input directory should be inside the ComfyUI directory
COMFY_UI_DIR = os.path.join(COMFY_ROOT, "ComfyUI")
COMFY_INPUT_DIR = os.path.join(COMFY_UI_DIR, "input")
COMFY_OUTPUT_DIR = os.path.join(COMFY_UI_DIR, "output")

# Create a directory to store our served images
SERVED_IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "served_images")
os.makedirs(SERVED_IMAGES_DIR, exist_ok=True)

logger.info(f"ComfyUI root directory: {COMFY_ROOT}")
logger.info(f"ComfyUI directory: {COMFY_UI_DIR}")
logger.info(f"ComfyUI input directory: {COMFY_INPUT_DIR}")
logger.info(f"ComfyUI output directory: {COMFY_OUTPUT_DIR}")

def verify_input_directory():
    """Verify that the input directory exists and is writable"""
    if not os.path.exists(COMFY_INPUT_DIR):
        raise RuntimeError(f"Input directory does not exist: {COMFY_INPUT_DIR}")
    if not os.access(COMFY_INPUT_DIR, os.W_OK):
        raise RuntimeError(f"Input directory is not writable: {COMFY_INPUT_DIR}")
    logger.info(f"Verified input directory: {COMFY_INPUT_DIR}")

# Verify input directory on startup
verify_input_directory()

def transform_to_img2img_workflow(data):
    """
    Transform frontend request data into ComfyUI workflow format for img2img
    """

    # Create workflow_request dictionary with the 4 keys expected by load_workflow
    workflow_request = {
        'generation_flow': 'img2img',
        'model_name': 'local',  # Default to local, will be updated based on actual model
        'controlnet': 'controlnet' in data,  # True if controlnet exists in data, False otherwise
        'lora': data.get('lora') is not None  # True if lora exists and is not None, False otherwise
    }
    
    # Determine model type based on model_name
    model_name = data.get('model_name', 'v1-6-pruned-emaonly-fp16.safetensors')
    if 'bfl' in model_name.lower() or 'flux' in model_name.lower():
        workflow_request['model_name'] = 'bfl'
    elif 'ideogram' in model_name.lower():  # Added check for ideogram models
        workflow_request['model_name'] = 'ideogram'
    else:
        workflow_request['model_name'] = 'local'
    
    print(f"\nWorkflow request dictionary:")
    print("-"*30)
    print(json.dumps(workflow_request, indent=2))
    print("-"*30)

    # Log the raw incoming data
    logger.info("Raw data received in transform_to_img2img_workflow:")
    logger.info(json.dumps({
        **data,
        'input_image': 'BASE64_IMAGE_DATA' if 'input_image' in data else None
    }, indent=2))

    # Get output directory using the shared function
    output_dir, _ = get_directories()
    logger.info(f"\nUsing output directory: {output_dir}")
    
    # Extract parameters with validation and type conversion
    prompt = data.get('prompt', '')
    negative_prompt = data.get('negative_prompt', '')
    width = max(64, min(2048, int(data.get('width', 512))))
    height = max(64, min(2048, int(data.get('height', 512))))
    batch_size = max(1, min(8, int(data.get('batch_size', 1))))
    steps = max(1, min(150, int(data.get('steps', 20))))
    cfg_scale = max(1.0, min(20.0, float(data.get('cfg_scale', 7.0))))
    denoising_strength = max(0.0, min(1.0, float(data.get('denoising_strength', 0.75))))
    input_image = data.get('input_image', '')
    model_name = data.get('model_name', 'v1-6-pruned-emaonly-fp16.safetensors')
    sampler_name = data.get('sampler_name', 'euler')
    scheduler = data.get('scheduler', 'normal')
    
    # Advanced settings
    vae_name = data.get('vae_name')
    clip_skip = data.get('clip_skip', 1)
    tiling = data.get('tiling', False)
    hires_fix = data.get('hires_fix', False)
    karras_sigmas = data.get('karras_sigmas', False)
    
    # Handle seed - ensure it's a positive integer
    try:
        seed = int(data.get('seed', 0))
    except (ValueError, TypeError):
        seed = 0
        
    # Generate a random positive seed if seed is 0 or negative
    if seed <= 0:
        seed = random.randint(1, 2**31 - 1)  # Using 2^31-1 as max to ensure it's well within safe integer range
        logger.info(f"Generated random seed: {seed}")
    
    # Update the data with the actual seed used
    data['seed'] = seed

    # Create core generation settings dictionary with all hardcoded values
    core_generation_settings = {
        'prompt': prompt,
        'negative_prompt': negative_prompt,
        'width': width,
        'height': height,
        'batch_size': batch_size,
        'steps': steps,
        'cfg': cfg_scale,
        'sampler_name': sampler_name,
        'scheduler': scheduler,
        'seed': seed,
        'ckpt_name': model_name,
        'denoise': 1.0,
        "image": os.path.join(COMFY_INPUT_DIR, input_image)
    }

    # Log the processed parameters
    logger.info("Core Generation Settings")
    logger.info(json.dumps(core_generation_settings, indent=4))
    
    # Create the ComfyUI workflow
    workflow = {
        "prompt": {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": cfg_scale,
                    "denoise": denoising_strength,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": sampler_name,
                    "scheduler": scheduler,
                    "seed": seed,
                    "steps": steps
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": model_name
                }
            },
            "5": {
                "class_type": "VAEEncode",
                "inputs": {
                    "pixels": ["resize", 0],
                    "vae": ["4", 2] if not vae_name else ["11", 0]
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": prompt
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": negative_prompt
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2] if not vae_name else ["11", 0]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                }
            },
            "10": {
                "class_type": "LoadImage",
                "inputs": {
                    "image": os.path.join(COMFY_INPUT_DIR, input_image)
                }
            },
            "resize": {
                "class_type": "ImageScale",
                "inputs": {
                    "image": ["10", 0],
                    "width": width,
                    "height": height,
                    "upscale": "disabled",
                    "crop": "center",
                    "upscale_method": "lanczos"
                }
            }
        }
    }

    # Add VAE loader if custom VAE is specified
    if vae_name:
        workflow["prompt"]["11"] = {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": vae_name
            }
        }
    
    loaded_workflow = load_workflow(workflow_request)
    print("\nLoaded workflow:")
    print("-"*50)
    print(json.dumps(loaded_workflow, indent=2))
    print("-"*50)
    
    # Check if custom workflow is provided and use it instead of the default workflow
    custom_workflow = data.get('custom_workflow')
    if custom_workflow and validate_custom_workflow(custom_workflow):
        logger.info("Custom workflow detected, updating with current parameters...")
        try:
            # Update the custom workflow with the current parameters
            workflow = update_custom_workflow(workflow, custom_workflow)
            logger.info("Successfully updated custom workflow with current parameters")
        except Exception as e:
            logger.error(f"Error updating custom workflow: {str(e)}")
            logger.info("Falling back to default workflow")
    else:
        # Update the default workflow with the current parameters
        workflow = override_workflow(loaded_workflow, core_generation_settings)
        # Update image paths in the workflow
        workflow = update_image_paths_in_workflow(workflow, os.path.join(COMFY_INPUT_DIR, input_image))
        logger.info("No valid custom workflow provided, using default workflow")
    
    # Log the generated workflow
    logger.info("Generated workflow:")
    logger.info(json.dumps(workflow, indent=2))
    
    # Inject API keys from environment variables into the workflow
    workflow = inject_api_keys_into_workflow(workflow)
    
    return workflow

def extract_filename_from_data_url(data_url):
    """Extract filename from data URL if present in the format data:image/...;name=filename.ext;base64,..."""
    if not data_url:
        return None
    
    # Try to find name parameter in the data URL
    name_match = re.search(r';name=(.*?);', data_url)
    if name_match:
        return name_match.group(1)
    return None

# Using shared functions from shared_utils.py

@app.route('/api/img2img', methods=['POST', 'OPTIONS'])
def handle_img2img():
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:8080')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    try:
        # Verify input directory before processing
        verify_input_directory()
        
        data = request.json
        logger.info("Received img2img request with data: %s", {
            **data,
            'input_image': 'BASE64_IMAGE_DATA' if 'input_image' in data else None
        })

        # Validate required fields
        required_fields = ['prompt', 'input_image', 'denoising_strength']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400

        # Process the input image
        try:
            # Get the input image from the request
            input_image = data['input_image']
            
            # Check if it's a data URL
            if input_image.startswith('data:'):
                # Extract the base64 part
                if ',' in input_image:
                    input_image = input_image.split(',')[1]
                
                # Decode base64 image
                image_bytes = base64.b64decode(input_image)
                image = Image.open(io.BytesIO(image_bytes))
            else:
                # If it's not a data URL, assume it's already base64 encoded
                image_bytes = base64.b64decode(input_image)
                image = Image.open(io.BytesIO(image_bytes))
            
            # Save the image temporarily in ComfyUI's input directory
            temp_filename = f"input_{int(time.time())}.png"
            temp_filepath = os.path.join(COMFY_INPUT_DIR, temp_filename)
            
            # Convert image to RGB if it's in RGBA mode
            if image.mode == 'RGBA':
                image = image.convert('RGB')
            elif image.mode not in ['RGB', 'L']:
                image = image.convert('RGB')
            
            # Save image and verify it was saved correctly
            image.save(temp_filepath, format='PNG')
            if not os.path.exists(temp_filepath):
                raise RuntimeError(f"Failed to save image to {temp_filepath}")
            
            # Verify the saved image can be opened
            try:
                with Image.open(temp_filepath) as verify_img:
                    verify_img.verify()
                logger.info(f"Verified saved image: {temp_filepath}")
            except Exception as e:
                raise RuntimeError(f"Saved image verification failed: {str(e)}")
            
            # Update the data with just the filename for the workflow
            data['input_image'] = temp_filename
            
            # Log image details
            logger.info("Input image saved as: %s, format=%s, size=%s, mode=%s", 
                       temp_filename, image.format, image.size, image.mode)
            
            # List directory contents for debugging
            logger.info("Input directory contents:")
            for filename in os.listdir(COMFY_INPUT_DIR):
                logger.info(f"  {filename}")
            
        except Exception as e:
            logger.error("Error processing input image: %s", str(e))
            return jsonify({
                'status': 'error',
                'message': f'Invalid input image: {str(e)}'
            }), 400

        # Transform data to ComfyUI workflow
        workflow = transform_to_img2img_workflow(data)
        
        # Log the workflow for debugging
        logger.info("Generated workflow:")
        logger.info(json.dumps(workflow, indent=2))
        
        # Send to ComfyUI
        comfy_response = send_to_comfyui(workflow)
        
        if "error" in comfy_response:
            return jsonify({
                "status": "error",
                "message": comfy_response["error"]
            }), 500
        
        # Log generated images if present
        if "generated_images" in comfy_response:
            images = comfy_response["generated_images"]
            logger.info("Generated Images Details:")
            for i, img in enumerate(images):
                logger.info(f"Image {i + 1}:")
                logger.info(f"  Filename: {img.get('filename')}")
                logger.info(f"  Type: {img.get('type')}")
                logger.info(f"  Subfolder: {img.get('subfolder', 'None')}")
                logger.info(f"  URL: {img.get('url')}")
        
        response = jsonify({
            "status": "success",
            "message": "Workflow sent to ComfyUI successfully",
            "comfy_response": comfy_response,
            "workflow": workflow
        })
        
        # Clean up the temporary image file
        try:
            os.remove(temp_filepath)
            logger.info(f"Cleaned up temporary file: {temp_filepath}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary file {temp_filepath}: {str(e)}")
        
        return response

    except Exception as e:
        logger.error("Error processing request: %s", str(e))
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/img2img/interrupt', methods=['POST'])
def handle_img2img_interrupt():
    print("=== IMG2IMG INTERRUPT REQUEST ===")
    print(request.json)
    return jsonify({"status": "received"})

@app.route('/images/<filename>')
def serve_image_endpoint(filename):
    """Serve images from the served_images directory"""
    try:
        # Use shared function
        from shared_utils import serve_image
        return serve_image(filename)
    except Exception as e:
        logger.error(f"Error serving image {filename}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True) 