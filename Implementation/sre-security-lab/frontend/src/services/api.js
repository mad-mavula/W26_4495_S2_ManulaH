import axios from 'axios';

export const API_URL = '';  // Use relative URLs, rely on nginx proxy

export const getScenarios = () => {
    return axios.get(`${API_URL}/scenarios`);
};

export const simulateScenario = (scenarioId) => {
    return axios.post(`${API_URL}/simulate/${scenarioId}`);
};

export const getHealth = () => {
    return axios.get(`${API_URL}/health`);
};

export const getRealtimeMetrics = (scenarioId) => {
    return axios.get(`${API_URL}/realtime-metrics/${scenarioId}`);
};
