import { RefreshCw, Save, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useEffect, useState, useCallback } from "react";
import {
  CheckpointModel,
  fetchAvailableModels,
  addModelRefreshListener,
  ensureWebSocketConnection
} from "@/services/modelService";
import { toast } from "@/components/ui/sonner";

interface ModelSelectorProps {
  onModelSelect: (modelName: string) => void;
}

const ModelSelector: React.FC<ModelSelectorProps> = ({ onModelSelect }) => {
  const [models, setModels] = useState<CheckpointModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isWebSocketConnected, setIsWebSocketConnected] = useState(false);
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null);

  const loadModels = useCallback(async (showSuccessToast = false) => {
    try {
      setIsLoading(true);
      setError(null);
      const availableModels = await fetchAvailableModels();
      setModels(availableModels);
      setLastRefreshTime(new Date());

      // If we have models and no selection, select the first one
      if (availableModels.length > 0 && !selectedModel) {
        setSelectedModel(availableModels[0].filename);
        onModelSelect(availableModels[0].filename);
      }

      // Show success toast for auto-refresh
      if (showSuccessToast) {
        toast.success(`Models refreshed! Found ${availableModels.length} models.`);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load models');
      console.error('Error loading models:', err);
      toast.error('Failed to refresh models');
    } finally {
      setIsLoading(false);
    }
  }, [selectedModel, onModelSelect]);

  // Setup WebSocket connection and model refresh listener
  useEffect(() => {
    // Initial model load
    loadModels();

    // Setup WebSocket connection
    const setupWebSocket = async () => {
      try {
        await ensureWebSocketConnection();
        setIsWebSocketConnected(true);
      } catch (error) {
        console.warn('⚠️ ModelSelector: Failed to establish WebSocket connection:', error);
        setIsWebSocketConnected(false);
      }
    };

    setupWebSocket();

    // Subscribe to model refresh events
    const unsubscribe = addModelRefreshListener(() => {
      console.log('📡 ModelSelector: Received model refresh event, reloading models...');
      loadModels(true); // Show success toast for auto-refresh
    });

    // Cleanup on unmount
    return () => {
      unsubscribe();
    };
  }, [loadModels]);

  const handleModelChange = (value: string) => {
    setSelectedModel(value);
    onModelSelect(value);
  };

  const handleManualRefresh = () => {
    loadModels();
  };

  const formatLastRefreshTime = (date: Date | null): string => {
    if (!date) return '';
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);

    if (diffSeconds < 60) {
      return `Updated ${diffSeconds}s ago`;
    } else if (diffMinutes < 60) {
      return `Updated ${diffMinutes}m ago`;
    } else {
      return `Updated at ${date.toLocaleTimeString()}`;
    }
  };

  return (
    <div className="flex flex-col space-y-3 sm:flex-row sm:items-center sm:space-x-4 sm:space-y-0">
      <div className="flex flex-col flex-1">
        <div className="flex items-center justify-between mb-1">
          <label htmlFor="model" className="text-sm font-medium">
            Select Stable Diffusion Checkpoint:
          </label>
          <div className="flex items-center space-x-2">
            {/* WebSocket Connection Status */}
            <div className="flex items-center space-x-1">
              {isWebSocketConnected ? (
                <Wifi className="h-3 w-3 text-green-500" title="Auto-refresh enabled" />
              ) : (
                <WifiOff className="h-3 w-3 text-gray-400" title="Auto-refresh disabled" />
              )}
              <span className="text-xs text-muted-foreground">
                {isWebSocketConnected ? 'Auto' : 'Manual'}
              </span>
            </div>
            {/* Last Refresh Time */}
            {lastRefreshTime && (
              <span className="text-xs text-muted-foreground">
                {formatLastRefreshTime(lastRefreshTime)}
              </span>
            )}
          </div>
        </div>
        <Select value={selectedModel} onValueChange={handleModelChange}>
          <SelectTrigger
            id="model"
            className="w-full bg-white dark:bg-[#0F172A] text-foreground dark:text-white border-input dark:border-slate-700"
          >
            <SelectValue placeholder="Select a model" />
          </SelectTrigger>
          <SelectContent className="bg-white dark:bg-[#0F172A] border-input dark:border-slate-700">
            {models.map((model) => (
              <SelectItem key={model.id} value={model.filename}>
                {model.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {error && <p className="text-sm text-red-500 mt-1">{error}</p>}
        {models.length === 0 && !isLoading && !error && (
          <p className="text-sm text-muted-foreground mt-1">
            No models found. Try uploading a new model file.
          </p>
        )}
      </div>
      <div className="flex flex-1 space-x-2 sm:justify-end">
        <Button
          variant="outline"
          className="flex items-center space-x-2 dark:bg-[#0F172A] dark:border-slate-700 dark:text-white dark:hover:bg-slate-800"
          onClick={handleManualRefresh}
          disabled={isLoading}
          title={isWebSocketConnected ? "Manual refresh (auto-refresh is active)" : "Refresh models"}
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>{isLoading ? 'Loading...' : 'Refresh'}</span>
        </Button>
        {false && <Button variant="outline" className="dark:bg-[#0F172A] dark:border-slate-700 dark:text-white dark:hover:bg-slate-800">
          <Save className="h-4 w-4 mr-2" />
          Saved Settings
        </Button>}
      </div>
    </div>
  );
};

export default ModelSelector;
