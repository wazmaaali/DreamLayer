export interface CheckpointModel {
  id: string;
  name: string;
  filename: string;
}

export const fetchAvailableModels = async (): Promise<CheckpointModel[]> => {
  try {
    const response = await fetch('http://localhost:5002/api/models');
    if (!response.ok) {
      throw new Error('Failed to fetch models');
    }
    
    const data = await response.json();
    if (data.status === 'success' && Array.isArray(data.models)) {
      return data.models;
    } else {
      throw new Error('Invalid response format');
    }
  } catch (error) {
    console.error('Error fetching models:', error);
    throw error;
  }
};

export interface RandomPromptResponse {
  status: string;
  message: string;
  type: string;
  prompt: string;
}

export const fetchRandomPrompt = async (type: 'positive' | 'negative'): Promise<string> => {
  try {
    console.log(`🔄 Frontend: Calling fetch-prompt API with type: ${type}`);
    const response = await fetch(`http://localhost:5002/api/fetch-prompt?type=${type}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch ${type} prompt: ${response.statusText}`);
    }
    
    const data: RandomPromptResponse = await response.json();
    console.log(`✅ Frontend: Received response:`, data);
    
    if (data.status === 'success') {
      return data.prompt;
    } else {
      throw new Error(data.message || 'Failed to fetch prompt');
    }
  } catch (error) {
    console.error(`❌ Frontend: Error fetching ${type} prompt:`, error);
    throw error;
  }
};

export const fetchUpscalerModels = async () => {
  const response = await fetch('http://localhost:5002/api/upscaler-models');
  const data = await response.json();
  return data.models;
};

export const fetchLoraModels = async () => {
  const response = await fetch('http://localhost:5002/api/lora-models');
  const data = await response.json();
  return data.models;
};

export const fetchControlNetModels = async () => {
  const response = await fetch('http://localhost:5001/api/controlnet/models');
  const data = await response.json();
  return data.models;
};

// Interface for unified model info across all types
export interface UnifiedModelInfo {
  id: string;
  name: string;
  filename: string;
  type: string;
  size?: number;
  dateAdded?: string;
  path?: string;
}

export const fetchAllModelTypes = async (): Promise<UnifiedModelInfo[]> => {
  try {
    const [checkpoints, loras, controlnets, upscalers] = await Promise.allSettled([
      fetchAvailableModels(),
      fetchLoraModels(),
      fetchControlNetModels(),
      fetchUpscalerModels()
    ]);

    const allModels: UnifiedModelInfo[] = [];

    // Process checkpoints
    if (checkpoints.status === 'fulfilled') {
      checkpoints.value.forEach((model: CheckpointModel) => {
        allModels.push({
          ...model,
          type: 'checkpoints',
          size: Math.floor(Math.random() * 5000000000), // Mock size for now
          dateAdded: new Date().toISOString(),
          path: `/models/checkpoints/${model.filename}`
        });
      });
    }

    // Process LoRAs
    if (loras.status === 'fulfilled') {
      loras.value.forEach((model: any) => {
        allModels.push({
          id: model.id || model.filename,
          name: model.name || model.filename.replace(/\.[^/.]+$/, ""),
          filename: model.filename,
          type: 'loras',
          size: Math.floor(Math.random() * 500000000), // Mock size for now
          dateAdded: new Date().toISOString(),
          path: `/models/loras/${model.filename}`
        });
      });
    }

    // Process ControlNet models
    if (controlnets.status === 'fulfilled') {
      controlnets.value.forEach((filename: string) => {
        allModels.push({
          id: filename,
          name: filename.replace(/\.[^/.]+$/, ""),
          filename: filename,
          type: 'controlnet',
          size: Math.floor(Math.random() * 2000000000), // Mock size for now
          dateAdded: new Date().toISOString(),
          path: `/models/controlnet/${filename}`
        });
      });
    }

    // Process Upscaler models
    if (upscalers.status === 'fulfilled') {
      upscalers.value.forEach((model: any) => {
        allModels.push({
          id: model.id || model.filename,
          name: model.name || model.filename.replace(/\.[^/.]+$/, ""),
          filename: model.filename,
          type: 'upscale_models',
          size: Math.floor(Math.random() * 1000000000), // Mock size for now
          dateAdded: new Date().toISOString(),
          path: `/models/upscale_models/${model.filename}`
        });
      });
    }

    return allModels;
  } catch (error) {
    console.error('Error fetching all model types:', error);
    throw error;
  }
};

// WebSocket Model Refresh Listener Types
export interface ModelRefreshEvent {
  model_type: string;
  filename: string;
  action: 'added' | 'removed';
  timestamp: number;
}

export interface WebSocketMessage {
  type: string;
  data: ModelRefreshEvent;
}

// WebSocket connection management
let wsConnection: WebSocket | null = null;
let wsReconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 2000; // 2 seconds
const WS_URL = 'ws://localhost:8188/ws';

// Generate a unique client ID for this session
const generateClientId = (): string => {
  return 'dreamlayer_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
};

// Model refresh listeners with optional model type filtering
interface ModelRefreshListener {
  callback: () => void;
  modelType?: string;
}

const modelRefreshListeners: Set<ModelRefreshListener> = new Set();

export const addModelRefreshListener = (
  callback: () => void,
  modelType?: string
): (() => void) => {
  const listener: ModelRefreshListener = { callback, modelType };
  modelRefreshListeners.add(listener);

  // Return unsubscribe function
  return () => {
    modelRefreshListeners.delete(listener);
  };
};

const notifyModelRefreshListeners = (event?: ModelRefreshEvent) => {
  modelRefreshListeners.forEach(listener => {
    try {
      // If listener has a model type filter, only notify for matching types
      if (listener.modelType && event?.model_type && listener.modelType !== event.model_type) {
        return; // Skip this listener
      }

      listener.callback();
    } catch (error) {
      console.error('Error in model refresh listener:', error);
    }
  });
};

const connectWebSocket = (): Promise<WebSocket> => {
  return new Promise((resolve, reject) => {
    try {
      const clientId = generateClientId();
      const wsUrl = `${WS_URL}?clientId=${clientId}`;

      console.log(`🔌 Connecting to ComfyUI WebSocket: ${wsUrl}`);

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('✅ WebSocket connected to ComfyUI');
        wsReconnectAttempts = 0;
        resolve(ws);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          // Listen for our custom "models-refresh" events
          if (message.type === 'models-refresh') {
            console.log('📡 Received model refresh event:', message.data);
            console.log('📡 Event model_type:', message.data?.model_type);
            console.log('📡 Event filename:', message.data?.filename);
            console.log('📡 Event action:', message.data?.action);
            notifyModelRefreshListeners(message.data);
          }

          // Also log other message types for debugging
          if (message.type !== 'status' && message.type !== 'executing') {
            console.log('📨 WebSocket message:', message.type, message.data);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        reject(error);
      };

      ws.onclose = (event) => {
        console.log('🔌 WebSocket connection closed:', event.code, event.reason);
        wsConnection = null;

        // Attempt to reconnect if not a clean close
        if (event.code !== 1000 && wsReconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          wsReconnectAttempts++;
          console.log(`🔄 Attempting to reconnect WebSocket (${wsReconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);

          setTimeout(() => {
            setupModelRefreshWebSocket().catch(error => {
              console.error('Failed to reconnect WebSocket:', error);
            });
          }, RECONNECT_DELAY * wsReconnectAttempts);
        }
      };

    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      reject(error);
    }
  });
};

export const setupModelRefreshWebSocket = async (): Promise<void> => {
  // Don't create multiple connections
  if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
    console.log('WebSocket already connected');
    return;
  }

  try {
    wsConnection = await connectWebSocket();
  } catch (error) {
    console.error('Failed to setup WebSocket connection:', error);
    throw error;
  }
};

export const closeModelRefreshWebSocket = (): void => {
  if (wsConnection) {
    console.log('🔌 Closing WebSocket connection');
    wsConnection.close(1000, 'Client disconnecting');
    wsConnection = null;
  }

  // Clear all listeners
  modelRefreshListeners.clear();
};

// Auto-setup WebSocket when this module is imported
// This ensures the connection is established early
let autoSetupPromise: Promise<void> | null = null;

export const ensureWebSocketConnection = (): Promise<void> => {
  if (!autoSetupPromise) {
    autoSetupPromise = setupModelRefreshWebSocket().catch(error => {
      console.warn('Failed to auto-setup WebSocket connection:', error);
      autoSetupPromise = null; // Reset so it can be retried
      throw error;
    });
  }

  return autoSetupPromise;
};