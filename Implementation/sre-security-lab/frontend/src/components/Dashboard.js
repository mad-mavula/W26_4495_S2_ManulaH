import React, { useState, useEffect } from 'react';
import { 
  Container, Grid, Paper, Typography, 
  Card, CardContent, Button, Alert,
  Chip, Box, LinearProgress
} from '@mui/material';
import { getScenarios, simulateScenario } from '../services/api';

function Dashboard() {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [simulationResult, setSimulationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchScenarios();
  }, []);

  const fetchScenarios = async () => {
    try {
      const response = await getScenarios();
      setScenarios(response.data);
    } catch (err) {
      setError('Failed to fetch scenarios');
    }
  };

  const handleSimulate = async (scenarioId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await simulateScenario(scenarioId);
      setSimulationResult(response.data);
    } catch (err) {
      setError('Simulation failed');
    } finally {
      setLoading(false);
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

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        SRE Security Research Lab
      </Typography>
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
            
            {scenarios.map((scenario) => (
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
        
        {/* Right Column - Simulation Results */}
        <Grid item xs={12} md={8}>
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
