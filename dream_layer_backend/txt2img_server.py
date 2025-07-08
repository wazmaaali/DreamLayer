from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import uuid
import time
import os
import shutil
import copy
import random
from dream_layer import get_directories
from dream_layer_backend_utils.update_custom_workflow import update_custom_workflow, validate_custom_workflow, find_save_node
from dream_layer_backend_utils.api_key_injector import inject_api_keys_into_workflow
from dream_layer_backend_utils.workflow_loader import load_workflow, analyze_workflow
from dream_layer_backend_utils.update_custom_workflow import override_workflow
from dream_layer_backend_utils import interrupt_workflow
from shared_utils import wait_for_image, send_to_comfyui, serve_image
from dream_layer_backend_utils.fetch_advanced_models import get_controlnet_models
from PIL import Image, ImageDraw

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:*", "http://127.0.0.1:*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

COMFY_API_URL = "http://127.0.0.1:8188"

# Sampler name mapping from frontend to ComfyUI
SAMPLER_NAME_MAP = {
    'Euler': 'euler',
    'Euler a': 'euler_ancestral',
    'LMS': 'lms',
    'Heun': 'heun',
    'DPM2': 'dpm_2',
    'DPM2 a': 'dpm_2_ancestral',
    'DPM++ 2S a': 'dpmpp_2s_ancestral',
    'DPM++ 2M': 'dpmpp_2m',
    'DPM++ SDE': 'dpmpp_sde',
    'DPM fast': 'dpm_fast',
    'DPM adaptive': 'dpm_adaptive',
    'LMS Karras': 'lms',
    'DPM2 Karras': 'dpm_2',
    'DPM2 a Karras': 'dpm_2_ancestral',
    'DPM++ 2S a Karras': 'dpmpp_2s_ancestral',
    'DPM++ 2M Karras': 'dpmpp_2m',
    'DPM++ SDE Karras': 'dpmpp_sde',
    'DDIM': 'ddim',
    'PLMS': 'plms'
}

# Get served images directory
output_dir, _ = get_directories()
SERVED_IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'served_images')
os.makedirs(SERVED_IMAGES_DIR, exist_ok=True)


def transform_to_txt2img_workflow(data):
    """
    Transform frontend data to ComfyUI txt2img workflow
    Combines advanced ControlNet functionality with smallFeatures improvements
    """
    try:
        print("\n🔄 Transforming txt2img workflow:")
        print("-" * 40)
        print(f"📊 Data keys: {list(data.keys())}")
        
        # Extract and validate core parameters with smallFeatures improvements
        prompt = data.get('prompt', '')
        negative_prompt = data.get('negative_prompt', '')
        
        # Dimension validation
        width = max(64, min(2048, int(data.get('width', 512))))
        height = max(64, min(2048, int(data.get('height', 512))))
        
        # Batch parameters with validation (from smallFeatures)
        batch_size = max(1, min(8, int(data.get('batch_size', 1))))  # Clamp between 1 and 8
        print(f"\nBatch size: {batch_size}")
        
        # Sampling parameters with validation
        steps = max(1, min(150, int(data.get('steps', 20))))
        cfg_scale = max(1.0, min(20.0, float(data.get('cfg_scale', 7.0))))
        
        # Get sampler name and map it to ComfyUI format (from smallFeatures)
        frontend_sampler = data.get('sampler_name', 'euler')
        sampler_name = SAMPLER_NAME_MAP.get(frontend_sampler, 'euler')
        print(f"\nMapping sampler name: {frontend_sampler} -> {sampler_name}")
        
        scheduler = data.get('scheduler', 'normal')
        
        # Handle seed - enhanced from smallFeatures for -1 values
        try:
            seed = int(data.get('seed', 0))
            if seed < 0:
                seed = random.randint(0, 2**32 - 1)  # Generate random seed between 0 and 2^32-1
        except (ValueError, TypeError):
            seed = random.randint(0, 2**32 - 1)
        
        # Handle model name validation
        model_name = data.get('model_name', 'juggernautXL_v8Rundiffusion.safetensors')
        
        # Check if it's a closed-source model (DALL-E, FLUX, Ideogram, etc.)
        closed_source_models = ['dall-e-3', 'dall-e-2', 'flux-pro', 'flux-dev', 'ideogram-v3']
        
        if model_name in closed_source_models:
            print(f"🎨 Using closed-source model: {model_name}")
        
        print(f"\nUsing model: {model_name}")
        
        core_generation_settings = {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'width': width,
            'height': height,
            'batch_size': batch_size,
            'steps': steps,
            'cfg_scale': cfg_scale,
            'sampler_name': sampler_name,
            'scheduler': scheduler,
            'seed': seed,
            'ckpt_name': model_name,
            'denoise': 1.0
        }
        print(f"🎯 Core settings: {core_generation_settings}")
        
        # Extract ControlNet data
        controlnet_data = data.get('controlnet', {})
        print(f"🎮 ControlNet data: {controlnet_data}")
        
        # Extract Face Restoration data
        face_restoration_data = {
            'restore_faces': data.get('restore_faces', False),
            'face_restoration_model': data.get('face_restoration_model', 'codeformer'),
            'codeformer_weight': data.get('codeformer_weight', 0.5),
            'gfpgan_weight': data.get('gfpgan_weight', 0.5)
        }
        print(f"👤 Face Restoration data: {face_restoration_data}")
        
        # Extract Tiling data
        tiling_data = {
            'tiling': data.get('tiling', False),
            'tile_size': data.get('tile_size', 512),
            'tile_overlap': data.get('tile_overlap', 64)
        }
        print(f"🧩 Tiling data: {tiling_data}")
        
        # Extract Hires.fix data
        hires_fix_data = {
            'hires_fix': data.get('hires_fix', False),
            'hires_fix_upscale_method': data.get('hires_fix_upscale_method', 'upscale-by'),
            'hires_fix_upscale_factor': data.get('hires_fix_upscale_factor', 2.5),
            'hires_fix_hires_steps': data.get('hires_fix_hires_steps', 1),
            'hires_fix_denoising_strength': data.get('hires_fix_denoising_strength', 0.5),
            'hires_fix_resize_width': data.get('hires_fix_resize_width', 4000),
            'hires_fix_resize_height': data.get('hires_fix_resize_height', 4000),
            'hires_fix_upscaler': data.get('hires_fix_upscaler', '4x-ultrasharp')
        }
        print(f"🖼️ Hires.fix data: {hires_fix_data}")
        
        # Extract Refiner data
        refiner_data = {
            'refiner_enabled': data.get('refiner_enabled', False),
            'refiner_model': data.get('refiner_model', 'none'),
            'refiner_switch_at': data.get('refiner_switch_at', 0.8)
        }
        print(f"🖌️ Refiner data: {refiner_data}")
        
        # Determine workflow template based on features
        use_controlnet = controlnet_data.get('enabled', False) and controlnet_data.get('units')
        use_lora = data.get('lora') and data.get('lora').get('enabled', False)
        use_face_restoration = face_restoration_data.get('restore_faces', False)
        use_tiling = tiling_data.get('tiling', False)
        
        print(f"🔧 Use ControlNet: {use_controlnet}")
        print(f"🔧 Use LoRA: {use_lora}")
        print(f"🔧 Use Face Restoration: {use_face_restoration}")
        print(f"🔧 Use Tiling: {use_tiling}")
        
        # Create workflow request for the loader
        if model_name in ['dall-e-3', 'dall-e-2']:
            workflow_model_type = 'dalle'
        elif model_name in ['flux-pro', 'flux-dev']:
            workflow_model_type = 'bfl'
        elif 'ideogram' in model_name.lower():  # Added check for ideogram models
            workflow_model_type = 'ideogram'
        else:
            workflow_model_type = 'local'
        
        workflow_request = {
            'generation_flow': 'txt2img',
            'model_name': workflow_model_type,
            'controlnet': use_controlnet,
            'lora': use_lora
        }
        
        print(f"📄 Workflow request: {workflow_request}")
        
        # Load workflow using the workflow loader
        workflow = load_workflow(workflow_request)
        print(f"✅ Workflow loaded successfully")
        
        # Inject API keys if needed (for DALL-E, FLUX, etc.)
        workflow = inject_api_keys_into_workflow(workflow)
        print(f"✅ API keys injected")
        
        # Custom workflow support from smallFeatures
        custom_workflow = data.get('custom_workflow')
        if custom_workflow and validate_custom_workflow(custom_workflow):
            print("Custom workflow detected, updating with current parameters...")
            try:
                workflow = update_custom_workflow(workflow, custom_workflow)
                print("Successfully updated custom workflow with current parameters")
            except Exception as e:
                print(f"Error updating custom workflow: {str(e)}")
                print("Falling back to default workflow override")
                workflow = override_workflow(workflow, core_generation_settings)
        else:
            # Apply overrides to loaded workflow
            workflow = override_workflow(workflow, core_generation_settings)
            print("No valid custom workflow provided, using default workflow with overrides")
        
        print(f"✅ Core settings applied")
        
        # Apply LoRA parameters if enabled
        if use_lora:
            print(f"🎨 Applying LoRA parameters...")
            workflow = inject_lora_parameters(workflow, data.get('lora', {}))
        
        # Apply ControlNet parameters if enabled
        if use_controlnet:
            print(f"🎮 Applying ControlNet parameters...")
            workflow = inject_controlnet_parameters(workflow, controlnet_data)
        
        # Apply Face Restoration parameters if enabled
        if use_face_restoration:
            print(f"👤 Applying Face Restoration parameters...")
            workflow = inject_face_restoration_parameters(workflow, face_restoration_data)
        
        # Apply Tiling parameters if enabled
        if use_tiling:
            print(f"🧩 Applying Tiling parameters...")
            workflow = inject_tiling_parameters(workflow, tiling_data)
        
        # Apply Hires.fix parameters if enabled
        if hires_fix_data.get('hires_fix', False):
            print(f"✨ Applying Hires.fix parameters...")
            workflow = inject_hires_fix_parameters(workflow, hires_fix_data)
        
        # Apply Refiner parameters if enabled
        if refiner_data.get('refiner_enabled', False):
            print(f"✨ Applying Refiner parameters...")
            workflow = inject_refiner_parameters(workflow, refiner_data)
        
        print(f"✅ Workflow transformation complete")
        print(f"📋 Generated workflow: {json.dumps(workflow, indent=2)}")
        return workflow
        
    except Exception as e:
        print(f"❌ Error transforming workflow: {str(e)}")
        import traceback
        traceback.print_exc()
        return None



# Using shared functions from shared_utils.py

@app.route('/api/txt2img', methods=['POST', 'OPTIONS'])
def handle_txt2img():
    """Handle text-to-image generation requests"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})
    
    try:
        data = request.json
        if data:
            print("Data:", json.dumps(data, indent=2))
            
            # Print specific fields of interest
            print("\nKey Parameters:")
            print("-"*20)
            print(f"Prompt: {data.get('prompt', 'Not provided')}")
            print(f"Negative Prompt: {data.get('negative_prompt', 'Not provided')}")
            print(f"Batch Size: {data.get('batch_size', 'Not provided')}")
            
            # Check ControlNet data specifically
            controlnet_data = data.get('controlnet', {})
            print(f"\n🎮 ControlNet Data:")
            print("-"*20)
            print(f"ControlNet enabled: {controlnet_data.get('enabled', False)}")
            if controlnet_data.get('units'):
                for i, unit in enumerate(controlnet_data['units']):
                    print(f"Unit {i}:")
                    print(f"  Enabled: {unit.get('enabled', False)}")
                    print(f"  Has input_image: {unit.get('input_image') is not None}")
                    print(f"  Input image type: {type(unit.get('input_image'))}")
                    if unit.get('input_image'):
                        print(f"  Input image length: {len(unit['input_image']) if isinstance(unit['input_image'], str) else 'N/A'}")
                        print(f"  Input image preview: {unit['input_image'][:50] if isinstance(unit['input_image'], str) else 'N/A'}...")
            else:
                print("No ControlNet units found")
            
            # Transform to ComfyUI workflow
            workflow = transform_to_txt2img_workflow(data)
            print("\nGenerated ComfyUI Workflow:")
            print("-"*20)
            print(json.dumps(workflow, indent=2))
            
            # Send to ComfyUI server
            comfy_response = send_to_comfyui(workflow)
            
            if "error" in comfy_response:
                return jsonify({
                    "status": "error",
                    "message": comfy_response["error"]
                }), 500
            
            response = jsonify({
                "status": "success",
                "message": "Workflow sent to ComfyUI successfully",
                "comfy_response": comfy_response,
                "generated_images": comfy_response.get("all_images", [])
            })
            
            return response
            
        else:
            return jsonify({
                "status": "error",
                "message": "No data received"
            }), 400
            
    except Exception as e:
        print(f"Error in handle_txt2img: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/txt2img/interrupt', methods=['POST'])
def handle_txt2img_interrupt():
    """Handle interruption of txt2img generation"""
    print("Interrupting txt2img generation...")
    success = interrupt_workflow()
    return jsonify({"status": "received", "interrupted": success})

@app.route('/api/images/<filename>', methods=['GET'])
def serve_image_endpoint(filename):
    """
    Serve images from multiple possible directories
    This endpoint is needed here because the frontend expects it on this port
    """
    try:
        # Use shared function
        from shared_utils import serve_image
        return serve_image(filename)
            
    except Exception as e:
        print(f"❌ Error serving image {filename}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/controlnet/models', methods=['GET'])
def get_controlnet_models_endpoint():
    """Get available ControlNet models"""
    try:
        models = get_controlnet_models()
        return jsonify({
            "status": "success",
            "models": models
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch ControlNet models: {str(e)}"
        }), 500

@app.route('/api/upload-controlnet-image', methods=['POST'])
def upload_controlnet_image_endpoint():
    """
    Endpoint to upload ControlNet images directly to ComfyUI input directory
    This endpoint is needed here because the frontend expects it on this port
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No file provided"
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "status": "error",
                "message": "No file selected"
            }), 400
        
        unit_index = request.form.get('unit_index', '0')
        try:
            unit_index = int(unit_index)
        except ValueError:
            unit_index = 0
        
        # Use shared function
        from shared_utils import upload_controlnet_image as upload_cn_image
        result = upload_cn_image(file, unit_index)
        
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        else:
            return jsonify(result)
            
    except Exception as e:
        print(f"❌ Error uploading ControlNet image: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == "__main__":
    print("\nStarting Text2Image Handler Server...")
    print("Listening for requests at http://localhost:5001/api/txt2img")
    print("ControlNet endpoints available:")
    print("  - GET /api/controlnet/models")
    print("  - POST /api/upload-controlnet-image")
    print("  - GET /api/images/<filename>")
    app.run(host='127.0.0.1', port=5001, debug=True) 