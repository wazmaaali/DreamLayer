import React, { useState, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Upload, FileText, CheckCircle, AlertCircle, X } from "lucide-react";
import { toast } from "@/components/ui/sonner";

// Model types supported by the backend
export type ModelType = 'checkpoints' | 'loras' | 'controlnet' | 'upscale_models' | 'vae' | 'embeddings' | 'hypernetworks';

export interface UploadedModel {
  filename: string;
  originalFilename: string;
  modelType: ModelType;
  filepath: string;
  size: number;
}

interface ModelDropZoneProps {
  onModelUploaded?: (model: UploadedModel) => void;
  acceptedTypes?: string[];
  modelType?: ModelType;
  className?: string;
}

const ModelDropZone: React.FC<ModelDropZoneProps> = ({
  onModelUploaded,
  acceptedTypes = ['.safetensors'],
  modelType = 'checkpoints',
  className = ""
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedModelType, setSelectedModelType] = useState<ModelType>(modelType);
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<UploadedModel | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Model type options with descriptions
  const modelTypeOptions = [
    { value: 'checkpoints', label: 'Checkpoints', description: 'Main Stable Diffusion models' },
    { value: 'loras', label: 'LoRAs', description: 'Low-Rank Adaptation models' },
    { value: 'controlnet', label: 'ControlNet', description: 'ControlNet models for guided generation' },
    { value: 'upscale_models', label: 'Upscalers', description: 'Image upscaling models' },
    { value: 'vae', label: 'VAE', description: 'Variational Autoencoder models' },
    { value: 'embeddings', label: 'Embeddings', description: 'Textual inversion embeddings' },
    { value: 'hypernetworks', label: 'Hypernetworks', description: 'Hypernetwork models' }
  ] as const;

  const validateFile = (file: File): string | null => {
    // Check file extension
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!acceptedTypes.includes(fileExtension)) {
      return `Invalid file type. Only ${acceptedTypes.join(', ')} files are supported.`;
    }

    // Check file size (8GB limit as per backend)
    const maxSize = 8 * 1024 * 1024 * 1024; // 8GB in bytes
    if (file.size > maxSize) {
      return 'File size exceeds 8GB limit.';
    }

    return null;
  };

  const uploadFile = async (file: File): Promise<UploadedModel> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('model_type', selectedModelType);

    const response = await fetch('http://localhost:5002/api/upload-model', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || `Upload failed: ${response.statusText}`);
    }

    const result = await response.json();
    if (result.status !== 'success') {
      throw new Error(result.message || 'Upload failed');
    }

    return {
      filename: result.filename,
      originalFilename: result.original_filename,
      modelType: result.model_type,
      filepath: result.filepath,
      size: result.size
    };
  };

  const handleFileUpload = async (file: File) => {
    // 🔒 RACE CONDITION PREVENTION: Block if already uploading
    if (isUploading) {
      console.log('Upload already in progress, ignoring new upload request');
      return;
    }

    const validationError = validateFile(file);
    if (validationError) {
      toast.error(validationError);
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setUploadedFile(null);

    try {
      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const uploadedModel = await uploadFile(file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      setUploadedFile(uploadedModel);
      onModelUploaded?.(uploadedModel);
      
      toast.success(`Model "${uploadedModel.originalFilename}" uploaded successfully!`);
      
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error(error instanceof Error ? error.message : 'Upload failed');
      setUploadProgress(0);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const handleBrowseClick = () => {
    if (!isUploading) {
      fileInputRef.current?.click();
    }
  };

  const handleClear = () => {
    setUploadedFile(null);
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Model Type Selection */}
      <div className="space-y-2">
        <Label htmlFor="model-type" className="text-sm font-medium">
          Model Type
        </Label>
        <Select 
          value={selectedModelType} 
          onValueChange={(value: ModelType) => setSelectedModelType(value)}
          disabled={isUploading}
        >
          <SelectTrigger 
            id="model-type"
            className="w-full bg-white dark:bg-[#0F172A] text-foreground dark:text-white border-input dark:border-slate-700"
          >
            <SelectValue placeholder="Select model type" />
          </SelectTrigger>
          <SelectContent className="bg-white dark:bg-[#0F172A] border-input dark:border-slate-700">
            {modelTypeOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                <div className="flex flex-col">
                  <span>{option.label}</span>
                  <span className="text-xs text-muted-foreground">{option.description}</span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Upload Area */}
      {uploadedFile ? (
        // Success State
        <div className="p-6 border-2 border-green-200 dark:border-green-800 rounded-lg bg-green-50 dark:bg-green-950/20">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400 mt-0.5" />
              <div className="flex-1">
                <h4 className="font-medium text-green-900 dark:text-green-100">
                  Upload Successful
                </h4>
                <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                  {uploadedFile.originalFilename}
                </p>
                <div className="flex items-center space-x-4 mt-2">
                  <Badge variant="secondary" className="text-xs">
                    {uploadedFile.modelType}
                  </Badge>
                  <span className="text-xs text-green-600 dark:text-green-400">
                    {formatFileSize(uploadedFile.size)}
                  </span>
                </div>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClear}
              className="text-green-700 dark:text-green-300 hover:text-green-900 dark:hover:text-green-100"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : (
        // Upload State
        <div 
          className={`
            relative p-8 border-2 border-dashed rounded-lg text-center transition-all duration-200
            ${dragActive 
              ? 'border-primary bg-primary/5 dark:bg-primary/10' 
              : 'border-border bg-card hover:bg-accent/50'
            }
            ${isUploading ? 'opacity-50 pointer-events-none' : 'cursor-pointer'}
          `}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={handleBrowseClick}
        >
          <div className="flex flex-col items-center space-y-4">
            {isUploading ? (
              <>
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                <div className="space-y-2 w-full max-w-xs">
                  <p className="text-sm text-muted-foreground">Uploading model...</p>
                  <Progress value={uploadProgress} className="w-full" />
                  <p className="text-xs text-muted-foreground">{uploadProgress}%</p>
                </div>
              </>
            ) : (
              <>
                <Upload className="h-12 w-12 text-muted-foreground" />
                <div className="space-y-2">
                  <p className="text-lg font-medium text-foreground">
                    Drop your model file here
                  </p>
                  <p className="text-sm text-muted-foreground">
                    or <span className="text-primary font-medium">browse files</span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Supports: {acceptedTypes.join(', ')} • Max size: 8GB
                  </p>
                </div>
                <Button variant="secondary" size="sm" className="mt-4">
                  <FileText className="h-4 w-4 mr-2" />
                  Browse Files
                </Button>
              </>
            )}
          </div>
          
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept={acceptedTypes.join(',')}
            onChange={handleFileInputChange}
            disabled={isUploading}
          />
        </div>
      )}
    </div>
  );
};

export default ModelDropZone;
