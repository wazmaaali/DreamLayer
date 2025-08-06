import React, { useState } from 'react';
import { AspectRatio } from "@/components/ui/aspect-ratio";
import { Button } from "@/components/ui/button";
import { useTxt2ImgGalleryStore } from '@/stores/useTxt2ImgGalleryStore';
import { useImg2ImgGalleryStore } from '@/stores/useImg2ImgGalleryStore';
import { Download, FolderOpen, Copy, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';
import JSZip from 'jszip';

interface ImagePreviewProps {
  onTabChange: (tabId: string) => void;
}

const LoadingAnimation = () => (
  <div className="animate-pulse space-y-4">
    <div className="h-full w-full bg-muted rounded-md flex items-center justify-center">
      <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
    </div>
  </div>
);

const ImagePreview: React.FC<ImagePreviewProps> = ({ onTabChange }) => {
  const { images, isLoading } = useTxt2ImgGalleryStore();
  const setInputImage = useImg2ImgGalleryStore(state => state.setInputImage);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [outputSettingsExpanded, setOutputSettingsExpanded] = useState(true);
  const [thumbnailStartIndex, setThumbnailStartIndex] = useState(0);

  const currentImage = images[selectedImageIndex] || images[0];
  const maxThumbnails = 5;
  const totalPages = Math.ceil(images.length / maxThumbnails);
  const currentPage = Math.floor(thumbnailStartIndex / maxThumbnails) + 1;

  const handleDownload = async (format: 'png' | 'zip') => {
    if (!currentImage) return;
    
    if (format === 'png') {
      // Download single PNG
      const link = document.createElement('a');
      link.href = currentImage.url;
      link.target = '_blank';
      link.download = `generated-image-${currentImage.id}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else if (format === 'zip') {
      // Download all images as ZIP
      const zip = new JSZip();
      const promises = images.map(async (image, index) => {
        const response = await fetch(image.url);
        const blob = await response.blob();
        zip.file(`generated-image-${index + 1}.png`, blob);
      });
      
      await Promise.all(promises);
      const zipBlob = await zip.generateAsync({type: 'blob'});
      
      const link = document.createElement('a');
      link.href = URL.createObjectURL(zipBlob);
      link.target = '_blank';
      link.download = 'generated-images.zip';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleShowInFolder = async () => {
    if (!currentImage) return;
    
    try {
      // Extract filename from URL (supports both old and new formats)
      const url = new URL(currentImage.url);
      let filename = url.searchParams.get('filename'); // Old ComfyUI format
      if (!filename) {
        // New format - extract from path
        filename = url.pathname.split('/').pop(); // Gets "image123.png"
      }
      
      if (!filename) {
        console.error('No filename found in URL:', currentImage.url);
        return;
      }
      console.log('=== Show in Folder Debug ===');
      console.log('Full URL:', currentImage.url);
      console.log('Extracted filename:', filename);
      console.log('Request body:', JSON.stringify({ filename }));
      console.log('Current Image:', currentImage);
      const response = await fetch('http://localhost:5002/api/show-in-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename })
      });
      
      const result = await response.json();
      console.log(result.message);
    } catch (error) {
      console.error('Error opening folder:', error);
    }
  };

  const handleSendTo = async (destination: 'img2img' | 'inpaint' | 'extras') => {
    if (!currentImage) return;
    
    if (destination === 'img2img') {
      try {
        // Extract filename from URL (supports both old and new formats)
        const url = new URL(currentImage.url);
        let filename = url.searchParams.get('filename'); // Old ComfyUI format
        if (!filename) {
          // New format - extract from path
          filename = url.pathname.split('/').pop(); // Gets "image123.png"
        }
        
        if (!filename) {
          console.error('No filename found in URL:', currentImage.url);
          return;
        }

        // Call our API endpoint
        const response = await fetch('http://localhost:5002/api/send-to-img2img', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename })
        });
        
        const result = await response.json();
        if (result.status === 'success') {
          // Use our server's images endpoint
          const imageUrl = `http://localhost:5001/api/images/${filename}`;
          const imageBlob = await fetch(imageUrl).then(r => r.blob());
          setInputImage({
            url: imageUrl,
            file: new File([imageBlob], filename)
          });
          
          // Switch to img2img tab
          onTabChange('img2img');
        }
      } catch (error) {
        console.error('Error sending to img2img:', error);
      }
    } else if (destination === 'extras') {
      try {
        // Extract filename from URL (supports both old and new formats)
        const url = new URL(currentImage.url);
        let filename = url.searchParams.get('filename'); // Old ComfyUI format
        if (!filename) {
          // New format - extract from path
          filename = url.pathname.split('/').pop(); // Gets "image123.png"
        }
        
        if (!filename) {
          console.error('No filename found in URL:', currentImage.url);
          return;
        }

        // Call our API endpoint
        const response = await fetch('http://localhost:5002/api/send-to-extras', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename })
        });
        
        const result = await response.json();
        if (result.status === 'success') {
          // Create a File object from the image URL
          const imageUrl = `http://localhost:5001/api/images/${filename}`;
          const imageBlob = await fetch(imageUrl).then(r => r.blob());
          const file = new File([imageBlob], filename);
          
          // Set the image in Extras component's state
          window.sessionStorage.setItem('extrasImage', JSON.stringify({
            file: {
              name: filename,
              size: imageBlob.size,
              type: imageBlob.type
            },
            preview: imageUrl
          }));
          
          // Switch to extras tab
          onTabChange('extras');
        }
      } catch (error) {
        console.error('Error sending to extras:', error);
      }
    } else {
      // TODO: Implement other destinations
      console.log(`Sending to ${destination}:`, currentImage);
    }
  };

  const handleCopyOutputSettings = () => {
    if (!currentImage?.settings) return;
    
    const settingsText = JSON.stringify(currentImage.settings, null, 2);
    navigator.clipboard.writeText(settingsText);
  };

  const handlePrevThumbnails = () => {
    setThumbnailStartIndex(Math.max(0, thumbnailStartIndex - maxThumbnails));
  };

  const handleNextThumbnails = () => {
    const newStartIndex = thumbnailStartIndex + maxThumbnails;
    if (newStartIndex < images.length) {
      setThumbnailStartIndex(newStartIndex);
    }
  };

  const handleThumbnailClick = (index: number) => {
    const actualIndex = thumbnailStartIndex + index;
    setSelectedImageIndex(actualIndex);
  };

  const formatSettingsDisplay = () => {
    if (!currentImage?.settings) return 'No settings available';
    
    const settings = currentImage.settings;
    const settingsAny = settings as any; // Type assertion for additional properties
    return `Prompt: ${currentImage.prompt || 'N/A'}

Negative prompt: ${currentImage.negativePrompt || 'N/A'}

Steps: ${settings.steps || 'N/A'}
Sampler: ${settings.sampler_name || 'N/A'}
CFG scale: ${settings.cfg_scale || 'N/A'}
Seed: ${settings.seed || 'N/A'}
Size: ${settings.width || 'N/A'}x${settings.height || 'N/A'}
Model hash: ${settingsAny.model_hash || 'N/A'}
Model: ${settings.model_name || 'N/A'}
Denoising strength: ${settings.denoising_strength || 'N/A'}
Version: v1.6.0
Networks not found: add-detail-xl, Double_Exposure
Time taken: 31.1 sec.`;
  };

  return (
    <div className="space-y-4">
      {/* Main Image Display */}
      <AspectRatio ratio={1} className="w-full">
        <div className="flex h-full w-full flex-col items-center justify-center rounded-md border border-border bg-card p-4">
          {isLoading ? (
            <LoadingAnimation />
          ) : images.length > 0 && currentImage ? (
            <div className="w-full h-full">
              <img 
                src={currentImage.url} 
                alt="Generated image" 
                className="w-full h-full object-cover rounded-md"
              />
            </div>
          ) : (
            <>
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-md bg-secondary">
                <svg
                  viewBox="0 0 24 24"
                  className="h-6 w-6 text-muted-foreground"
                  fill="none"
                  stroke="currentColor"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <path d="m21 15-5-5L5 21" />
                </svg>
              </div>
              <p className="text-sm text-muted-foreground">Generated Images Will Display Here</p>
            </>
          )}
        </div>
      </AspectRatio>

      {/* Thumbnail Navigation */}
      {images.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-center gap-2 px-4">
            {/* Left Arrow */}
            {images.length > maxThumbnails && (
              <Button
                variant="ghost"
                size="sm"
                className="h-16 w-8 p-0 hover:bg-accent"
                onClick={handlePrevThumbnails}
                disabled={thumbnailStartIndex === 0}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            )}

            {/* Thumbnails */}
            <div className="flex gap-2">
              {images.slice(thumbnailStartIndex, thumbnailStartIndex + maxThumbnails).map((image, index) => {
                const actualIndex = thumbnailStartIndex + index;
                return (
                  <button
                    key={image.id}
                    onClick={() => handleThumbnailClick(index)}
                    className={`w-16 h-16 rounded border-2 transition-colors overflow-hidden ${
                      actualIndex === selectedImageIndex 
                        ? 'border-primary' 
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <img 
                      src={image.url} 
                      alt={`Generated image ${actualIndex + 1}`}
                      className="w-full h-full object-cover"
                    />
                  </button>
                );
              })}
              
              {/* Show empty squares if less than maxThumbnails images in current page */}
              {images.slice(thumbnailStartIndex, thumbnailStartIndex + maxThumbnails).length < maxThumbnails && 
               thumbnailStartIndex + maxThumbnails >= images.length &&
               Array.from({ 
                 length: maxThumbnails - images.slice(thumbnailStartIndex, thumbnailStartIndex + maxThumbnails).length 
               }).map((_, index) => (
                <div 
                  key={`empty-${index}`}
                  className="w-16 h-16 rounded"
                  style={{ backgroundColor: '#f1f1f1' }}
                />
              ))}
            </div>

            {/* Right Arrow */}
            {images.length > maxThumbnails && (
              <Button
                variant="ghost"
                size="sm"
                className="h-16 w-8 p-0 hover:bg-accent"
                onClick={handleNextThumbnails}
                disabled={thumbnailStartIndex + maxThumbnails >= images.length}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            )}
          </div>

          {/* Pagination Indicator */}
          {images.length > maxThumbnails && (
            <div className="flex justify-center">
              <div className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                {currentPage} / {totalPages}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Action Sections */}
      {images.length > 0 && currentImage && (
        <div className="space-y-4 px-4">
          {/* Download Section */}
          <div>
            <div className="flex items-center flex-wrap gap-2">
              <span className="text-sm font-medium">Download:</span>
              <Button 
                variant="outline" 
                size="sm" 
                className="text-xs h-8"
                onClick={() => handleDownload('png')}
              >
                <Download className="w-3 h-3 mr-1" />
                PNG
              </Button>
              {false && <Button 
                variant="outline" 
                size="sm" 
                className="text-xs h-8"
                onClick={() => handleDownload('zip')}
              >
                <Download className="w-3 h-3 mr-1" />
                ZIP
              </Button>}
              <Button 
                variant="outline" 
                size="sm" 
                className="text-xs h-8"
                onClick={handleShowInFolder}
              >
                <FolderOpen className="w-3 h-3 mr-1" />
                Show in Folder
              </Button>
            </div>
          </div>

          {/* Send To Section */}
          <div>
            <div className="flex items-center flex-wrap gap-2">
              <span className="text-sm font-medium">Send To:</span>
              <Button 
                variant="outline" 
                size="sm" 
                className="text-xs h-8"
                onClick={() => handleSendTo('img2img')}
              >
                Img2Img
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                className="text-xs h-8"
                onClick={() => handleSendTo('inpaint')}
              >
                Inpaint
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                className="text-xs h-8"
                onClick={() => handleSendTo('extras')}
              >
                Extras
              </Button>
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-border"></div>

          {/* Output Settings Section */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium">Output Settings</span>
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="text-xs h-8"
                  onClick={handleCopyOutputSettings}
                >
                  <Copy className="w-3 h-3 mr-1" />
                  Copy Output Settings
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={() => setOutputSettingsExpanded(!outputSettingsExpanded)}
                >
                  <ChevronDown className={`w-4 h-4 transition-transform ${outputSettingsExpanded ? 'rotate-180' : ''}`} />
                </Button>
              </div>
            </div>
            
            {outputSettingsExpanded && (
              <div className="bg-muted p-3 rounded-md text-xs leading-relaxed">
                <div className="space-y-3">
                  <div>
                    <div className="font-semibold mb-1">Prompt:</div>
                    <div className="text-muted-foreground break-words">{currentImage.prompt || 'N/A'}</div>
                  </div>
                  
                  <div>
                    <div className="font-semibold mb-1">Negative prompt:</div>
                    <div className="text-muted-foreground break-words">{currentImage.negativePrompt || 'N/A'}</div>
                  </div>
                  
                  <div className="space-y-2">
                    <div><strong>Steps:</strong> {currentImage.settings?.steps || 'N/A'}</div>
                    <div><strong>Sampler:</strong> {currentImage.settings?.sampler_name || 'N/A'}</div>
                    <div><strong>CFG scale:</strong> {currentImage.settings?.cfg_scale || 'N/A'}</div>
                    <div><strong>Seed:</strong> {currentImage.settings?.seed || 'N/A'}</div>
                    <div><strong>Size:</strong> {currentImage.settings?.width || 'N/A'}x{currentImage.settings?.height || 'N/A'}</div>
                    <div><strong>Model:</strong> {currentImage.settings?.model_name || 'N/A'}</div>
                    {currentImage.settings?.denoising_strength && (
                      <div><strong>Denoising strength:</strong> {currentImage.settings.denoising_strength}</div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ImagePreview; 