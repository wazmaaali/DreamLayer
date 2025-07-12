import os
import shutil
import time
import requests
import copy
from typing import List, Dict, Any
from pathlib import Path
from dream_layer import get_directories
from dream_layer_backend_utils.update_custom_workflow import find_save_node
from dream_layer_backend_utils.shared_workflow_parameters import increment_seed_in_workflow

# Global constants
COMFY_API_URL = "http://127.0.0.1:8188"
SERVED_IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'served_images')

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
os.makedirs(SERVED_IMAGES_DIR, exist_ok=True)

def wait_for_image(prompt_id: str, save_node_id: str = "9", max_wait_time: int = 300) -> List[Dict[str, Any]]:
    """
    Wait for image generation to complete and return the generated images
    This is a shared function used by both txt2img and img2img servers
    """
    output_dir, _ = get_directories()
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            # Check queue status
            response = requests.get(f"{COMFY_API_URL}/queue")
            if response.status_code == 200:
                queue_data = response.json()
                
                # Check if our prompt is still in queue
                running_queue = queue_data.get('queue_running', [])
                pending_queue = queue_data.get('queue_pending', [])
                
                # Look for our prompt_id in running or pending queues
                prompt_in_queue = any(item[1] == prompt_id for item in running_queue + pending_queue)
                
                if not prompt_in_queue:
                    # Prompt is no longer in queue, check for results
                    history_response = requests.get(f"{COMFY_API_URL}/history/{prompt_id}")
                    if history_response.status_code == 200:
                        history_data = history_response.json()
                        if prompt_id in history_data:
                            # Get outputs from the save node
                            outputs = history_data[prompt_id].get('outputs', {})
                            if save_node_id in outputs:
                                images_data = outputs[save_node_id].get('images', [])
                                print(f"📸 Found {len(images_data)} images in save node {save_node_id}")
                                if images_data:
                                    image_objects = []
                                    for img_info in images_data:
                                        filename = img_info.get('filename')
                                        print(f"📄 Processing image: {filename}")
                                        if filename:
                                            # Copy to served images directory
                                            src_path = os.path.join(output_dir, filename)
                                            dest_path = os.path.join(SERVED_IMAGES_DIR, filename)
                                            
                                            print(f"📁 Source path: {src_path}")
                                            print(f"📁 Destination path: {dest_path}")
                                            print(f"📁 Source exists: {os.path.exists(src_path)}")
                                            print(f"📁 Dest dir exists: {os.path.exists(SERVED_IMAGES_DIR)}")
                                            
                                            if os.path.exists(src_path):
                                                try:
                                                    shutil.copy2(src_path, dest_path)
                                                    print(f"✅ Successfully copied {filename} to served directory")
                                                    # Create proper image object with URL
                                                    image_objects.append({
                                                        "filename": filename,
                                                        "url": f"http://localhost:5001/api/images/{filename}",
                                                        "type": "output",
                                                        "subfolder": ""
                                                    })
                                                except Exception as copy_error:
                                                    print(f"❌ Error copying {filename}: {copy_error}")
                                            else:
                                                print(f"❌ Source file not found: {src_path}")
                                    
                                    if image_objects:
                                        print(f"🎉 Returning {len(image_objects)} image objects")
                                        return image_objects
                                    else:
                                        print("⚠️ No image objects created")
                                else:
                                    print("⚠️ No images found in save node")
            
            time.sleep(2)  # Wait 2 seconds before checking again
            
        except Exception as e:
            print(f"Error checking image status: {e}")
            time.sleep(2)
    
    print(f"Timeout waiting for image generation (prompt_id: {prompt_id})")
    return []

def send_to_comfyui(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send workflow to ComfyUI and handle the response
    This is a shared function used by both txt2img and img2img servers
    """
    try:
        from dream_layer_backend_utils.workflow_loader import analyze_workflow
        workflow_info = analyze_workflow(workflow)
        batch_size = workflow_info['batch_size']
        
        if workflow_info['is_api']:
            # API workflows: remove batch_size, loop multiple times
            for node in workflow.get('prompt', {}).values():
                if 'batch_size' in node.get('inputs', {}):
                    del node['inputs']['batch_size']
                    break
            iterations = batch_size
        else:
            # Local workflows: keep batch_size, loop once
            iterations = 1
        
        all_images = []
        last_response_data = None
        
        for i in range(iterations):
            # Increment seed for variation

            current_workflow = increment_seed_in_workflow(copy.deepcopy(workflow), i) if i > 0 else workflow
            
            # Send to ComfyUI
            response = requests.post(f"{COMFY_API_URL}/prompt", json=current_workflow)
            
            if response.status_code == 200:
                response_data = response.json()
                last_response_data = response_data
                if "prompt_id" in response_data:
                    save_node_id = find_save_node(current_workflow) or "9"
                    print(f"🔍 Found save node ID: {save_node_id}")
                    images = wait_for_image(response_data["prompt_id"], save_node_id)
                    if images:
                        all_images.extend(images)
                    print(f"Iteration {i+1}/{iterations} completed")
                else:
                    print(f"Error in iteration {i+1}: {response_data}")
                    return {"error": f"ComfyUI API error: {response_data}"}
            else:
                error_msg = f"ComfyUI server error: {response.status_code} - {response.text}"
                print(error_msg)
                return {"error": error_msg}
        
        if all_images:
            # Return the last valid ComfyUI response but with all images
            if last_response_data:
                last_response_data["all_images"] = all_images
                last_response_data["generated_images"] = all_images
            return last_response_data
        else:
            return {"error": "No images were generated"}
            
    except Exception as e:
        error_msg = f"Error sending workflow to ComfyUI: {str(e)}"
        print(error_msg)
        return {"error": error_msg}

def serve_image(filename: str) -> Any:
    """
    Serve images from multiple possible directories
    This is a shared function used by all servers
    """
    from flask import send_file, jsonify
    
    try:
        # First check in served_images directory (for generated images)
        served_filepath = os.path.join(SERVED_IMAGES_DIR, filename)
        
        if os.path.exists(served_filepath):
            return send_file(served_filepath, mimetype='image/png')
        
        # If not found in served_images, check in ComfyUI input directory (for ControlNet images)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        input_dir = os.path.join(parent_dir, "ComfyUI", "input")
        input_filepath = os.path.join(input_dir, filename)
        
        if os.path.exists(input_filepath):
            return send_file(input_filepath, mimetype='image/png')
        
        # If not found in either location, check ComfyUI output directory
        output_dir, _ = get_directories()
        output_filepath = os.path.join(output_dir, filename)
        
        if os.path.exists(output_filepath):
            return send_file(output_filepath, mimetype='image/png')
        
        # If still not found, return 404
        print(f"❌ Image not found in any directory: {filename}")
        print(f"   Checked: {served_filepath}")
        print(f"   Checked: {input_filepath}")
        print(f"   Checked: {output_filepath}")
        
        return jsonify({
            "status": "error",
            "message": "Image not found"
        }), 404
            
    except Exception as e:
        print(f"❌ Error serving image {filename}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def upload_controlnet_image(file, unit_index: int = 0) -> Dict[str, Any]:
    """
    Upload ControlNet images to ComfyUI input directory
    This is a shared function used by multiple servers
    """
    try:
        print("🖼️ ControlNet image upload request received")
        
        if not file or file.filename == '':
            return {
                "status": "error",
                "message": "No file provided or no file selected"
            }, 400
        
        print(f"📁 Uploading file: {file.filename} for unit {unit_index}")
        print(f"📊 File content type: {file.content_type}")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        input_dir = os.path.join(project_root, "ComfyUI", "input")
        print(f"📁 Target directory: {input_dir}")
        
        os.makedirs(input_dir, exist_ok=True)
        
        timestamp = int(time.time() * 1000)
        filename = f"controlnet_unit_{unit_index}_{timestamp}.png"
        filepath = os.path.join(input_dir, filename)
        
        print(f"📄 Saving to: {filepath}")
        file.save(filepath)
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"✅ Successfully saved ControlNet image: {filename}")
            print(f"📏 File size: {file_size} bytes")
            
            return {
                "status": "success",
                "filename": filename,
                "url": f"/api/images/{filename}",
                "filepath": filepath,
                "size": file_size
            }
        else:
            print(f"❌ File was not created: {filepath}")
            return {
                "status": "error",
                "message": "Failed to save file"
            }, 500
            
    except Exception as e:
        print(f"❌ Error uploading ControlNet image: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e)
        }, 500


def upload_model_file(file, model_type: str = "checkpoints") -> Dict[str, Any]:
    """
    Upload .safetensors model files to appropriate ComfyUI model directories
    Implements atomic write and path traversal protection

    Args:
        file: Flask file object from request.files
        model_type: Type of model (checkpoints, loras, controlnet, upscale_models, etc.)

    Returns:
        Dict containing status, filename, and other metadata
    """
    try:
        print(f"🤖 Model upload request received for type: {model_type}")

        if not file or file.filename == '':
            return {
                "status": "error",
                "message": "No file provided or no file selected"
            }, 400

        # Validate file extension - only .safetensors for now
        allowed_extensions = {'.safetensors'}
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in allowed_extensions:
            return {
                "status": "error",
                "message": f"Invalid file type. Only .safetensors files are supported"
            }, 400

        print(f"📁 Uploading model: {file.filename}")
        print(f"📊 File content type: {file.content_type}")
        print(f"🏷️ Model type: {model_type}")

        # Get ComfyUI models directory structure
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        comfyui_models_dir = os.path.join(project_root, "ComfyUI", "models")

        # Map model types to directories
        model_type_dirs = {
            "checkpoints": "checkpoints",
            "loras": "loras",
            "controlnet": "controlnet",
            "upscale_models": "upscale_models",
            "vae": "vae",
            "embeddings": "embeddings",
            "hypernetworks": "hypernetworks"
        }

        if model_type not in model_type_dirs:
            return {
                "status": "error",
                "message": f"Invalid model type. Allowed: {', '.join(model_type_dirs.keys())}"
            }, 400

        target_dir = os.path.join(comfyui_models_dir, model_type_dirs[model_type])

        # 🔒 SECURITY: Prevent path traversal attacks
        models_base_dir = Path(comfyui_models_dir).resolve()
        target_dir_path = Path(target_dir).resolve()

        if not target_dir_path.is_relative_to(models_base_dir):
            print(f"❌ Path traversal attempt detected: {target_dir}")
            return {
                "status": "error",
                "message": "Invalid target directory"
            }, 400

        # Create target directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)
        print(f"📁 Target directory: {target_dir}")

        # Generate safe filename with timestamp
        timestamp = int(time.time() * 1000)
        safe_filename = f"{Path(file.filename).stem}_{timestamp}{file_ext}"
        target_path = Path(target_dir) / safe_filename

        # 🔒 SECURITY: Final path validation
        final_target_path = target_path.resolve()
        if not final_target_path.is_relative_to(models_base_dir):
            print(f"❌ Final path traversal check failed: {final_target_path}")
            return {
                "status": "error",
                "message": "Invalid file path"
            }, 400

        print(f"📄 Saving to: {target_path}")

        # 🔒 ATOMIC WRITE: Write to temporary file first
        temp_path = target_path.with_suffix(target_path.suffix + '.tmp')

        try:
            # Save to temporary file
            file.save(str(temp_path))

            # Force write to disk (fsync)
            with open(temp_path, 'rb') as f:
                os.fsync(f.fileno())

            # Atomic rename to final destination
            temp_path.rename(target_path)

            print(f"✅ Atomic write completed: {safe_filename}")

        except Exception as e:
            # Clean up temp file if something went wrong
            if temp_path.exists():
                temp_path.unlink()
            raise e

        # Verify file was created successfully
        if target_path.exists():
            file_size = target_path.stat().st_size
            print(f"✅ Successfully saved model: {safe_filename}")
            print(f"📏 File size: {file_size} bytes")

            return {
                "status": "success",
                "filename": safe_filename,
                "original_filename": file.filename,
                "model_type": model_type,
                "filepath": str(target_path),
                "size": file_size,
                "message": f"Model uploaded successfully to {model_type}"
            }
        else:
            print(f"❌ File was not created: {target_path}")
            return {
                "status": "error",
                "message": "Failed to save file"
            }, 500

    except Exception as e:
        print(f"❌ Error uploading model: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e)
        }, 500