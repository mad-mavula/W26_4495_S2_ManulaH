import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Container, Grid, Paper, Typography, 
  Button, Alert, Chip, Box, LinearProgress
} from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { API_URL } from '../services/api';

function Dashboard() {
  const [incidents, setIncidents] = useState([]);
  const [error, setError] = useState(null);
  const [metrics, setMetrics] = useState({
    request_rate: [],
    auth_failures: [],
    latency_p95: [],
    cpu_usage: [],
    memory_usage: []
  });
  const [loading, setLoading] = useState(true);
  const [attackLoading, setAttackLoading] = useState(false);

  // Fetch classifier history and merge with existing incidents (never lose incidents)
  const fetchIncidents = async () => {
    try {
      const response = await axios.get(`${API_URL}/classifier/history?limit=500`);
      const data = response.data;
      if (Array.isArray(data)) {
        // Merge new incidents with existing ones, avoid duplicates by incident_id
        setIncidents(prev => {
          const combined = [...prev, ...data];
          const unique = combined.filter((inc, index, self) =>
            index === self.findIndex(i => i.incident_id === inc.incident_id)
          );
          // Sort by timestamp descending (newest first for display)
          unique.sort((a, b) => b.timestamp - a.timestamp);
          // Keep only last 500 to avoid memory bloat
          return unique.slice(0, 500);
        });
      } else {
        console.warn('Backend returned non-array data:', data);
      }
    } catch (err) {
      console.error('Failed to fetch incidents', err);
      // Do not clear incidents on error – keep existing
    }
  };

  // Fetch metric history for a given metric name
  const fetchMetricHistory = async (metricName) => {
    try {
      const response = await axios.get(`${API_URL}/metrics-history/${metricName}`);
      const data = response.data;
      if (data.values && Array.isArray(data.values)) {
        const formatted = data.values.map(([ts, val]) => ({
          time: new Date(ts * 1000).toLocaleTimeString(),
          value: parseFloat(val)
        }));
        setMetrics(prev => ({ ...prev, [metricName]: formatted }));
      }
    } catch (err) {
      console.error(`Failed to fetch ${metricName} history`, err);
    }
  };

  // Fetch all metrics
  const fetchAllMetrics = async () => {
    const metricNames = ['request_rate', 'auth_failures', 'latency_p95', 'cpu_usage', 'memory_usage'];
    await Promise.all(metricNames.map(fetchMetricHistory));
    setLoading(false);
  };

  // Poll incidents and metrics every 2 seconds
  useEffect(() => {
    fetchIncidents();
    fetchAllMetrics();
    const interval = setInterval(() => {
      fetchIncidents();
      fetchAllMetrics();
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const clearClassifierHistory = async () => {
    try {
      await axios.post(`${API_URL}/classifier/clear`);
      await axios.post(`${API_URL}/detector/clear`);
      setIncidents([]);  // Clear only when user clicks the button
      setError(null);
    } catch (err) {
      console.error('Failed to clear classifier history', err);
      setError('Failed to clear classifier history');
    }
  };

  const resetDetector = async () => {
    try {
      await axios.post(`${API_URL}/detector/stop`);
      await axios.post(`${API_URL}/detector/start`);
      await axios.post(`${API_URL}/classifier/clear`);
      setIncidents([]);  // Clear on reset as well
      setError(null);
    } catch (err) {
      console.error('Failed to reset detector', err);
      setError('Failed to reset detector');
    }
  };

  const runAttack = async (attackType) => {
    setAttackLoading(true);
    try {
      const response = await axios.post(`${API_URL}/run-attack/${attackType}`);
      if (response.data.status === 'success') {
        console.log(`Attack ${attackType} started`);
      } else {
        setError(`Failed to start ${attackType} attack: ${response.data.message}`);
      }
    } catch (err) {
      console.error(`Failed to run ${attackType} attack`, err);
      setError(`Failed to run ${attackType} attack`);
    } finally {
      setAttackLoading(false);
    }
  };

  const getIncidentColor = (type) => {
    if (type === 'security') return 'error';
    if (type === 'operational') return 'info';
    return 'default';
  };

  const MetricChart = ({ title, dataKey, color, unit }) => (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Typography variant="h6" gutterBottom>{title}</Typography>
      {loading ? (
        <LinearProgress />
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={metrics[dataKey]}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" tick={{ fontSize: 10 }} />
            <YAxis unit={unit} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="value" stroke={color} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Paper>
  );

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">SRE Security Research Lab</Typography>
        <Box>
          <Button variant="contained" color="secondary" onClick={() => runAttack('bruteforce')} disabled={attackLoading} sx={{ mr: 1 }}>
            Run Brute Force
          </Button>
          <Button variant="contained" color="primary" onClick={() => runAttack('ddos')} disabled={attackLoading} sx={{ mr: 1 }}>
            Run DDoS
          </Button>
          <Button variant="outlined" onClick={resetDetector} sx={{ mr: 1 }}>
            Reset Detector
          </Button>
          <Button variant="outlined" onClick={clearClassifierHistory}>
            Clear Live Incidents
          </Button>
        </Box>
      </Box>
      <Typography variant="subtitle1" color="textSecondary" gutterBottom>
        Live Metrics & Incident Classification
      </Typography>
      
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <MetricChart title="Request Rate (req/sec)" dataKey="request_rate" color="#8884d8" unit=" req/s" />
          <MetricChart title="Authentication Failures (401/sec)" dataKey="auth_failures" color="#ff7300" unit=" /s" />
          <MetricChart title="Latency p95 (seconds)" dataKey="latency_p95" color="#82ca9d" unit=" s" />
          <MetricChart title="CPU Usage (cores)" dataKey="cpu_usage" color="#ffc658" unit=" cores" />
          <MetricChart title="Memory Usage (MB)" dataKey="memory_usage" color="#d62728" unit=" MB" />
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              Live Incidents
            </Typography>
            <Typography variant="body2" color="textSecondary" paragraph>
              Automatically updated from the classifier
            </Typography>
            {incidents.length === 0 ? (
              <Typography color="textSecondary" sx={{ textAlign: 'center', mt: 4 }}>
                No incidents yet. Run an attack simulation.
              </Typography>
            ) : (
              <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
                {incidents.map((inc, idx) => (
                  <Paper key={idx} sx={{ p: 1, mb: 1, borderLeft: 4, borderColor: getIncidentColor(inc.incident_type) }}>
                    <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                      <Chip label={inc.attack_guess || inc.incident_type} size="small" color={getIncidentColor(inc.incident_type)} />
                      {inc.incident_type !== 'normal' && (
                        <Typography variant="caption">Severity: {inc.severity}</Typography>
                      )}
                      <Typography variant="caption">Confidence: {inc.confidence}%</Typography>
                    </Box>
                    <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                      {inc.explanation?.user_impact}
                    </Typography>
                  </Paper>
                ))}
              </div>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}

export default Dashboard;
