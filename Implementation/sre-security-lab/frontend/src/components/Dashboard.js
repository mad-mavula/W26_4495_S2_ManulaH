import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Container, Grid, Paper, Typography, 
  Card, CardContent, Button, Alert,
  Chip, Box, LinearProgress, List, ListItem, ListItemText
} from '@mui/material';
import { getScenarios, simulateScenario, API_URL } from '../services/api';

function Dashboard() {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [simulationResult, setSimulationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [useRealMetrics, setUseRealMetrics] = useState(false);
  const [incidents, setIncidents] = useState([]);

  // Fetch classifier history
  const fetchIncidents = async () => {
    try {
      const response = await axios.get(`${API_URL}/classifier/history`);
      const data = response.data;
      setIncidents(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch incidents', err);
    }
  };

  // Poll incidents every 5 seconds
  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchScenarios();
  }, []);

  const fetchScenarios = async () => {
    try {
      const response = await getScenarios();
      const data = response.data;
      setScenarios(Array.isArray(data) ? data : []);
    } catch (err) {
      setError('Failed to fetch scenarios');
      setScenarios([]);
    }
  };

  const handleSimulate = async (scenarioId) => {
    setLoading(true);
    setError(null);
    try {
      let response;
      if (useRealMetrics) {
        response = await axios.get(`${API_URL}/realtime-metrics/${scenarioId}`);
      } else {
        response = await simulateScenario(scenarioId);
      }
      setSimulationResult(response.data);
    } catch (err) {
      setError('Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = async () => {
    try {
      await axios.post(`${API_URL}/classifier/clear`);
      await axios.post(`${API_URL}/detector/clear`);
      setSimulationResult(null);
      setError(null);
      setIncidents([]);
    } catch (err) {
      console.error('Failed to clear history', err);
      setError('Failed to clear history');
    }
  };

  const getSeverityColor = (riskLevel) => {
    switch(riskLevel) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'success';
      default: return 'info';
    }
  };

  const getIncidentColor = (type) => {
    if (type === 'security') return 'error';
    if (type === 'operational') return 'info';
    return 'default';
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">SRE Security Research Lab</Typography>
        <Box>
          <Button variant="outlined" onClick={clearHistory} sx={{ mr: 2 }}>
            Clear History
          </Button>
          <Button 
            variant={useRealMetrics ? "contained" : "outlined"}
            color={useRealMetrics ? "primary" : "default"}
            onClick={() => setUseRealMetrics(!useRealMetrics)}
          >
            {useRealMetrics ? "Using Real Metrics" : "Using Simulated Data"}
          </Button>
        </Box>
      </Box>
      <Typography variant="subtitle1" color="textSecondary" gutterBottom>
        Incident Classification & Prioritization Framework
      </Typography>
      
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      
      <Grid container spacing={3}>
        {/* Left Column - Scenarios List */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Incident Scenarios
            </Typography>
            <Typography variant="body2" color="textSecondary" paragraph>
              Select a scenario to simulate and analyze
            </Typography>
            
            {Array.isArray(scenarios) && scenarios.map((scenario) => (
              <Card 
                key={scenario.id} 
                sx={{ 
                  mb: 2, 
                  bgcolor: selectedScenario === scenario.id ? '#e3f2fd' : 'white',
                  border: selectedScenario === scenario.id ? '2px solid #1976d2' : 'none'
                }}
              >
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="subtitle1">
                      {scenario.name}
                    </Typography>
                    <Chip 
                      label={scenario.type} 
                      size="small"
                      color={scenario.type === 'security' ? 'error' : 'info'}
                    />
                  </Box>
                  <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                    {scenario.description}
                  </Typography>
                  <Button 
                    variant="contained" 
                    size="small"
                    sx={{ mt: 2 }}
                    onClick={() => {
                      setSelectedScenario(scenario.id);
                      handleSimulate(scenario.id);
                    }}
                    disabled={loading}
                  >
                    Simulate
                  </Button>
                </CardContent>
              </Card>
            ))}
          </Paper>
        </Grid>
        
        {/* Middle Column - Live Incidents */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Live Incidents
            </Typography>
            <Typography variant="body2" color="textSecondary" paragraph>
              Automatically updated from the classifier
            </Typography>
            {!Array.isArray(incidents) || incidents.length === 0 ? (
              <Typography color="textSecondary" sx={{ textAlign: 'center', mt: 4 }}>
                No incidents yet. Run an attack simulation.
              </Typography>
            ) : (
              <List dense>
                {incidents.slice().reverse().map((inc, idx) => (
                  <ListItem key={idx} divider>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Chip 
                            label={inc.attack_guess || inc.incident_type} 
                            size="small"
                            color={getIncidentColor(inc.incident_type)}
                          />
                          <Typography variant="caption">Severity: {inc.severity}</Typography>
                        </Box>
                      }
                      secondary={
                        <>
                          <Typography variant="caption" display="block">
                            Type: {inc.incident_type}
                          </Typography>
                          <Typography variant="caption" display="block">
                            Confidence: {inc.confidence}%
                          </Typography>
                          <Typography variant="caption" display="block">
                            {inc.explanation?.user_impact}
                          </Typography>
                        </>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        {/* Right Column - Simulation Results */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, minHeight: '500px' }}>
            <Typography variant="h6" gutterBottom>
              Simulation Results
            </Typography>
            
            {loading && <LinearProgress sx={{ my: 2 }} />}
            
            {simulationResult ? (
              <Box>
                <Box display="flex" gap={1} mb={2}>
                  <Chip 
                    label={`Type: ${simulationResult.type}`}
                    color={simulationResult.type === 'security' ? 'error' : 'info'}
                  />
                  <Chip 
                    label={`Risk: ${simulationResult.analysis.risk_level}`}
                    color={getSeverityColor(simulationResult.analysis.risk_level)}
                  />
                </Box>
                
                <Typography variant="subtitle2" gutterBottom>
                  Metrics Detected:
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: '#f5f5f5' }}>
                  <pre style={{ margin: 0, overflow: 'auto' }}>
                    {JSON.stringify(simulationResult.metrics, null, 2)}
                  </pre>
                </Paper>
                
                <Typography variant="subtitle2" gutterBottom>
                  Recommendations:
                </Typography>
                <ul>
                  {simulationResult.analysis.recommendations.map((rec, index) => (
                    <li key={index}>
                      <Typography variant="body2">{rec}</Typography>
                    </li>
                  ))}
                </ul>
                
                <Typography variant="caption" color="textSecondary">
                  Simulation ID: {simulationResult.simulation_id}
                </Typography>
              </Box>
            ) : (
              <Box 
                display="flex" 
                justifyContent="center" 
                alignItems="center" 
                minHeight="300px"
              >
                <Typography color="textSecondary">
                  Select a scenario from the left to begin simulation
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}

export default Dashboard;
