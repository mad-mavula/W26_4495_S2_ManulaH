import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://192.168.49.2:30182/api';

export const getScenarios = () => {
    return axios.get(`${API_URL}/scenarios`);
};

export const simulateScenario = (scenarioId) => {
    return axios.post(`${API_URL}/simulate/${scenarioId}`);
};

export const getHealth = () => {
    return axios.get(`${API_URL}/health`);
};
