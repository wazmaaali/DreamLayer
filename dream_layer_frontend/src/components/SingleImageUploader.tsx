import React from 'react';
import { Button } from "@/components/ui/button";
import ImageUploadButton from './ImageUploadButton';
import { useImg2ImgGalleryStore } from '@/stores/useImg2ImgGalleryStore';

interface SingleImageUploaderProps {
  onDrop?: (e: React.DragEvent) => void;
  onDragOver?: (e: React.DragEvent) => void;
}

const SingleImageUploader: React.FC<SingleImageUploaderProps> = ({
  onDrop,
  onDragOver
}) => {
  const { inputImage, setInputImage } = useImg2ImgGalleryStore();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setInputImage({ url, file });
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setInputImage({ url, file });
    }
    onDrop?.(e);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    onDragOver?.(e);
  };

  const handleClear = () => {
    if (inputImage?.url) {
      URL.revokeObjectURL(inputImage.url);
    }
    setInputImage(null);
  };

  return (
    <div className="flex justify-center">
      <div className="w-full max-w-sm">
        {inputImage ? (
          <div className="relative">
            <img 
              src={inputImage.url} 
              alt="Input image" 
              className="rounded-md object-cover w-full aspect-square border border-border"
            />
            <div className="absolute bottom-2 right-2 flex gap-1">
              <Button 
                variant="outline" 
                size="sm" 
                className="bg-background/80 backdrop-blur-sm border-border text-foreground hover:bg-accent"
                onClick={handleClear}
              >
                Clear
              </Button>
            </div>
          </div>
        ) : (
          <div 
            className="p-4 border-2 border-dashed border-border rounded-md text-center flex flex-col items-center justify-center aspect-square bg-card"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            <p className="text-muted-foreground mb-2">Drag & drop an image here</p>
            <p className="text-xs text-muted-foreground mb-4">PNG, JPG, WEBP or GIF up to 10MB</p>
            <ImageUploadButton onFileChange={handleFileChange}>
              Browse Files
            </ImageUploadButton>
          </div>
        )}
      </div>
    </div>
  );
};

export default SingleImageUploader;
