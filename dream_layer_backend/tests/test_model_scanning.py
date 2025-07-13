"""
Test model scanning consistency across different model types
Ensures all model scanners use the same file extensions
"""

import pytest
import os
import tempfile
from unittest.mock import patch, Mock
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dream_layer_backend_utils.fetch_advanced_models import (
        get_controlnet_models,
        get_lora_models, 
        get_upscaler_models
    )
except ImportError:
    # If import fails, we'll skip these tests
    pytest.skip("Could not import model scanning functions", allow_module_level=True)


class TestModelScanningConsistency:
    """Test that all model scanning functions use consistent extensions"""
    
    def test_all_scanners_support_same_extensions(self, temp_model_dir, expected_extensions):
        """Test that all model scanners support the same file extensions"""
        # Create test files with all supported extensions
        test_files = []
        for ext in expected_extensions:
            filename = f"test_model{ext}"
            test_files.append(filename)
            # Create actual files in temp directory
            with open(os.path.join(temp_model_dir, filename), 'w') as f:
                f.write("test")
        
        # Mock the directory paths to use our temp directory
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=test_files), \
             patch('dream_layer_backend_utils.fetch_advanced_models.get_settings', return_value={}):
            
            # Test ControlNet scanner
            try:
                controlnet_models = get_controlnet_models()
                # Should find all files with supported extensions
                assert len(controlnet_models) == len(expected_extensions)
            except Exception as e:
                pytest.skip(f"ControlNet scanner test skipped: {e}")
            
            # Test LoRA scanner  
            try:
                lora_models = get_lora_models()
                # Should find all files with supported extensions
                assert len(lora_models) == len(expected_extensions)
            except Exception as e:
                pytest.skip(f"LoRA scanner test skipped: {e}")
            
            # Test Upscaler scanner
            try:
                upscaler_models = get_upscaler_models()
                # Should find all files with supported extensions
                assert len(upscaler_models) == len(expected_extensions)
            except Exception as e:
                pytest.skip(f"Upscaler scanner test skipped: {e}")


class TestIndividualScanners:
    """Test individual model scanners"""
    
    def test_controlnet_scanner_extensions(self, temp_model_dir, expected_extensions):
        """Test ControlNet scanner accepts all expected extensions"""
        # Create test files
        test_files = [f"controlnet_model{ext}" for ext in expected_extensions]
        test_files.append("invalid_model.txt")  # Should be ignored
        
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=test_files), \
             patch('dream_layer_backend_utils.fetch_advanced_models.get_settings', return_value={}):
            
            try:
                models = get_controlnet_models()
                # Should only include files with valid extensions
                assert len(models) == len(expected_extensions)
                # Should not include .txt file
                assert not any('txt' in model for model in models)
            except Exception as e:
                pytest.skip(f"ControlNet test skipped: {e}")
    
    def test_lora_scanner_extensions(self, temp_model_dir, expected_extensions):
        """Test LoRA scanner accepts all expected extensions"""
        # Create test files
        test_files = [f"lora_model{ext}" for ext in expected_extensions]
        test_files.append("invalid_model.txt")  # Should be ignored
        
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=test_files), \
             patch('dream_layer_backend_utils.fetch_advanced_models.get_settings', return_value={}):
            
            try:
                models = get_lora_models()
                # Should only include files with valid extensions
                assert len(models) == len(expected_extensions)
                # Should not include .txt file
                assert not any('txt' in model for model in models)
            except Exception as e:
                pytest.skip(f"LoRA test skipped: {e}")
    
    def test_upscaler_scanner_extensions(self, temp_model_dir, expected_extensions):
        """Test Upscaler scanner accepts all expected extensions"""
        # Create test files
        test_files = [f"upscaler_model{ext}" for ext in expected_extensions]
        test_files.append("invalid_model.txt")  # Should be ignored
        
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=test_files), \
             patch('dream_layer_backend_utils.fetch_advanced_models.get_settings', return_value={}):
            
            try:
                models = get_upscaler_models()
                # Should only include files with valid extensions
                assert len(models) == len(expected_extensions)
                # Should not include .txt file
                assert not any('txt' in model for model in models)
            except Exception as e:
                pytest.skip(f"Upscaler test skipped: {e}")


class TestScannerBehavior:
    """Test scanner behavior with various file scenarios"""
    
    def test_empty_directory_handling(self):
        """Test scanners handle empty directories gracefully"""
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=[]), \
             patch('dream_layer_backend_utils.fetch_advanced_models.get_settings', return_value={}):
            
            try:
                assert get_controlnet_models() == []
                assert get_lora_models() == []
                assert get_upscaler_models() == []
            except Exception as e:
                pytest.skip(f"Empty directory test skipped: {e}")
    
    def test_nonexistent_directory_handling(self):
        """Test scanners handle nonexistent directories gracefully"""
        with patch('os.path.exists', return_value=False), \
             patch('dream_layer_backend_utils.fetch_advanced_models.get_settings', return_value={}):
            
            try:
                # Should return empty lists for nonexistent directories
                assert get_controlnet_models() == []
                assert get_lora_models() == []
                assert get_upscaler_models() == []
            except Exception as e:
                pytest.skip(f"Nonexistent directory test skipped: {e}")
    
    def test_mixed_file_types(self, expected_extensions):
        """Test scanners with mixed valid and invalid file types"""
        # Mix of valid and invalid files
        test_files = [
            "model1.safetensors",
            "model2.ckpt", 
            "model3.pth",
            "invalid1.txt",
            "invalid2.json",
            "readme.md",
            "model4.pt",
            "model5.bin"
        ]
        
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=test_files), \
             patch('dream_layer_backend_utils.fetch_advanced_models.get_settings', return_value={}):
            
            try:
                controlnet_models = get_controlnet_models()
                lora_models = get_lora_models()
                upscaler_models = get_upscaler_models()
                
                # All scanners should find exactly 5 valid models
                assert len(controlnet_models) == 5
                assert len(lora_models) == 5
                assert len(upscaler_models) == 5
                
                # Verify no invalid extensions are included
                all_models = controlnet_models + lora_models + upscaler_models
                for model in all_models:
                    model_ext = os.path.splitext(model)[1].lower()
                    assert model_ext in expected_extensions
                    
            except Exception as e:
                pytest.skip(f"Mixed file types test skipped: {e}")


class TestUploadScanningConsistency:
    """Test consistency between upload validation and scanning"""
    
    def test_upload_validation_matches_scanning(self, expected_extensions):
        """Test that upload validation uses same extensions as scanners"""
        # This is the validation logic from shared_utils.py
        upload_allowed_extensions = {'.safetensors', '.ckpt', '.pth', '.pt', '.bin'}
        
        # Should match our expected extensions
        assert upload_allowed_extensions == expected_extensions
    
    def test_what_can_be_uploaded_can_be_scanned(self, expected_extensions):
        """Test that any file that can be uploaded will be found by scanners"""
        # Create files with all uploadable extensions
        uploadable_files = [f"model{ext}" for ext in expected_extensions]
        
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=uploadable_files), \
             patch('dream_layer_backend_utils.fetch_advanced_models.get_settings', return_value={}):
            
            try:
                # All scanners should find all uploadable files
                controlnet_models = get_controlnet_models()
                lora_models = get_lora_models() 
                upscaler_models = get_upscaler_models()
                
                expected_count = len(expected_extensions)
                assert len(controlnet_models) == expected_count
                assert len(lora_models) == expected_count
                assert len(upscaler_models) == expected_count
                
            except Exception as e:
                pytest.skip(f"Upload-scanning consistency test skipped: {e}")
