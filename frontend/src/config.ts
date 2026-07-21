// Backend API base URL. Set VITE_API_URL at build/deploy time (see .env.example);
// falls back to the local dev backend when unset.
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
