import axios from 'axios';

// This holds the ID once resolved, acting as the "Universal" reference for the UI
let currentProjectId: string | null = null;

export const setGlobalProjectContext = (id: string) => {
    currentProjectId = id;
};

const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL
});

// Universal Interceptor: Automatically injects project context into every POST/PUT
api.interceptors.request.use((config) => {
    if (currentProjectId && config.method !== 'get') {
        // We inject it into the body if it's a JSON request
        if (config.data && typeof config.data === 'object') {
            config.data.project_id = currentProjectId;
        }
    }
    return config;
});

export default api;