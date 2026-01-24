import { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, TrendingUp, TrendingDown, DollarSign, Power, Settings, Play, Pause, AlertCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Input } from './ui/input';
import { Card } from './ui/card';
import { Label } from './ui/label';
import { toast } from 'sonner';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace('https', 'wss').replace('http', 'ws');

const PRIVATE_KEY = '4kdnHjgYy7eDwdm2TZKth8Kf5mtFdx5FSFniJkaaBJH7NYdemfpBn7WApAXQst4KmFhrgfs1QmsebiZhHqVdTLUt';

function Dashboard() {
  const [botRunning, setBotRunning] = useState(false);
  const [paperTrading, setPaperTrading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [positions, setPositions] = useState([]);
  const [stats, setStats] = useState({
    total_trades: 0,
    winning_trades: 0,
    losing_trades: 0,
    win_rate: 0,
    total_pnl_sol: 0,
    active_positions: 0
  });
  const [activityLog, setActivityLog] = useState([]);
  const [config, setConfig] = useState({
    amount_per_trade: 0.1,
    take_profit_percent: 12,
    stop_loss_percent: 30,
    time_exit_minutes: 6,
    liquidity_drop_percent: 30,
    slippage: 5
  });
  const [ws, setWs] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const addLog = useCallback((message, type = 'info') => {
    setActivityLog(prev => [
      {
        message,
        type,
        timestamp: new Date().toLocaleTimeString()
      },
      ...prev.slice(0, 99)
    ]);
  }, []);

  const connectWebSocket = useCallback(() => {
    const websocket = new WebSocket(`${WS_URL}/api/ws`);
    
    websocket.onopen = () => {
      console.log('WebSocket connected');
      setWsConnected(true);
      setReconnectAttempts(0);
      addLog('Connected to real-time updates', 'success');
      
      // Send ping every 30 seconds to keep connection alive
      const pingInterval = setInterval(() => {
        if (websocket.readyState === WebSocket.OPEN) {
          websocket.send(JSON.stringify({ type: 'ping' }));
        } else {
          clearInterval(pingInterval);
        }
      }, 30000);
      
      websocket.pingInterval = pingInterval;
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'new_tokens') {
          addLog(`${data.data.length} new token(s) found`, 'info');
        } else if (data.type === 'update') {
          setPositions(data.data.positions || []);
          setStats(data.data.stats || stats);
        } else if (data.type === 'trade') {
          addLog(`Trade executed: ${data.data.action} ${data.data.token}`, 'success');
        } else if (data.type === 'position_closed') {
          const pos = data.data;
          const pnlColor = pos.pnl_sol >= 0 ? 'success' : 'error';
          addLog(`Position closed: ${pos.token} | PnL: ${pos.pnl_sol.toFixed(4)} SOL (${pos.pnl_percent.toFixed(2)}%)`, pnlColor);
        }
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsConnected(false);
    };

    websocket.onclose = () => {
      console.log('WebSocket closed');
      setWsConnected(false);
      
      if (websocket.pingInterval) {
        clearInterval(websocket.pingInterval);
      }
      
      // Auto-reconnect with exponential backoff
      if (reconnectAttempts < 10) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
        addLog(`Reconnecting in ${delay/1000}s...`, 'warning');
        setTimeout(() => {
          setReconnectAttempts(prev => prev + 1);
          connectWebSocket();
        }, delay);
      } else {
        addLog('Max reconnection attempts reached', 'error');
      }
    };

    setWs(websocket);
    return websocket;
  }, [addLog, reconnectAttempts]);

  useEffect(() => {
    const websocket = connectWebSocket();

    return () => {
      if (websocket) {
        if (websocket.pingInterval) {
          clearInterval(websocket.pingInterval);
        }
        websocket.close();
      }
    };
  }, []);

  const handleStartStop = async () => {
    setLoading(true);
    try {
      const action = botRunning ? 'stop' : 'start';
      const payload = {
        action,
        config: action === 'start' ? {
          private_key: PRIVATE_KEY,
          ...config,
          paper_trading: paperTrading
        } : undefined
      };

      const response = await axios.post(`${API}/bot/control`, payload);
      
      if (response.data.status === 'started') {
        setBotRunning(true);
        toast.success(`Bot started in ${paperTrading ? 'PAPER' : 'LIVE'} mode`);
        addLog(`Bot started (${paperTrading ? 'PAPER' : 'LIVE'} trading)`, 'success');
      } else if (response.data.status === 'stopped') {
        setBotRunning(false);
        toast.info('Bot stopped');
        addLog('Bot stopped', 'warning');
      }
    } catch (error) {
      console.error('Error controlling bot:', error);
      toast.error('Failed to control bot');
      addLog('Error controlling bot', 'error');
    } finally {
      setLoading(false);
    }
  };

  const formatSOL = (value) => {
    return value?.toFixed(4) || '0.0000';
  };

  const formatPercent = (value) => {
    return value?.toFixed(2) || '0.00';
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-white p-4">
      <div className="max-w-[1920px] mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight" style={{fontFamily: 'Manrope'}}>Solana Trading Bot</h1>
            <div className="flex items-center gap-3 mt-1">
              <p className="text-zinc-500 text-sm">Tactical Terminal v1.0</p>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-[#22C55E]' : 'bg-[#EF4444]'} animate-pulse`}></div>
                <span className={`text-xs ${wsConnected ? 'text-[#22C55E]' : 'text-[#EF4444]'}`}>
                  {wsConnected ? 'Live' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-[#121214] border border-zinc-800 rounded-sm px-4 py-2">
              <Label className="text-sm text-zinc-400">Paper Trading</Label>
              <Switch
                data-testid="paper-trading-toggle"
                checked={paperTrading}
                onCheckedChange={setPaperTrading}
                disabled={botRunning}
              />
            </div>
            
            <Button
              data-testid="start-stop-bot-button"
              onClick={handleStartStop}
              disabled={loading}
              className={`${botRunning ? 'bg-red-900/20 text-red-500 border-red-900/50 hover:bg-red-900/40' : 'bg-[#14F195] text-black hover:bg-[#14F195]/90'} font-bold uppercase tracking-wider text-xs rounded-sm px-6`}
            >
              {loading ? (
                'Loading...'
              ) : botRunning ? (
                <><Pause className="w-4 h-4 mr-2" /> Stop Bot</>
              ) : (
                <><Play className="w-4 h-4 mr-2" /> Start Bot</>
              )}
            </Button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-6 gap-4 mb-6">
          <Card className="bg-[#121214] border-zinc-800 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase tracking-wider" style={{fontFamily: 'JetBrains Mono'}}>Total Trades</p>
                <p className="text-2xl font-bold mt-1" style={{fontFamily: 'JetBrains Mono'}}>{stats.total_trades}</p>
              </div>
              <Activity className="w-8 h-8 text-[#14F195]" />
            </div>
          </Card>

          <Card className="bg-[#121214] border-zinc-800 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase tracking-wider" style={{fontFamily: 'JetBrains Mono'}}>Win Rate</p>
                <p className="text-2xl font-bold mt-1" style={{fontFamily: 'JetBrains Mono'}}>{formatPercent(stats.win_rate)}%</p>
              </div>
              <TrendingUp className="w-8 h-8 text-[#22C55E]" />
            </div>
          </Card>

          <Card className="bg-[#121214] border-zinc-800 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase tracking-wider" style={{fontFamily: 'JetBrains Mono'}}>Total PnL</p>
                <p className={`text-2xl font-bold mt-1 ${stats.total_pnl_sol >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'}`} style={{fontFamily: 'JetBrains Mono'}}>
                  {formatSOL(stats.total_pnl_sol)} SOL
                </p>
              </div>
              <DollarSign className="w-8 h-8 text-[#9945FF]" />
            </div>
          </Card>

          <Card className="bg-[#121214] border-zinc-800 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase tracking-wider" style={{fontFamily: 'JetBrains Mono'}}>Winning</p>
                <p className="text-2xl font-bold mt-1 text-[#22C55E]" style={{fontFamily: 'JetBrains Mono'}}>{stats.winning_trades}</p>
              </div>
              <TrendingUp className="w-8 h-8 text-[#22C55E]" />
            </div>
          </Card>

          <Card className="bg-[#121214] border-zinc-800 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase tracking-wider" style={{fontFamily: 'JetBrains Mono'}}>Losing</p>
                <p className="text-2xl font-bold mt-1 text-[#EF4444]" style={{fontFamily: 'JetBrains Mono'}}>{stats.losing_trades}</p>
              </div>
              <TrendingDown className="w-8 h-8 text-[#EF4444]" />
            </div>
          </Card>

          <Card className="bg-[#121214] border-zinc-800 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase tracking-wider" style={{fontFamily: 'JetBrains Mono'}}>Active</p>
                <p className="text-2xl font-bold mt-1" style={{fontFamily: 'JetBrains Mono'}}>{stats.active_positions}</p>
              </div>
              <Power className="w-8 h-8 text-[#3B82F6]" />
            </div>
          </Card>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-12 gap-4">
          {/* Positions Table */}
          <div className="col-span-8">
            <Card className="bg-[#121214] border-zinc-800 rounded-sm p-4">
              <div className="border-b border-zinc-800 pb-3 mb-3 flex justify-between items-center">
                <h2 className="text-lg font-bold" style={{fontFamily: 'Manrope'}}>Active Positions</h2>
                <span className="text-xs text-zinc-500" style={{fontFamily: 'JetBrains Mono'}}>{positions.length} positions</span>
              </div>
              
              <div className="overflow-auto" style={{maxHeight: '400px'}}>
                <table className="w-full text-sm text-left">
                  <thead className="sticky top-0 bg-[#121214] z-10">
                    <tr className="text-zinc-500 font-mono text-xs uppercase tracking-wider border-b border-zinc-800">
                      <th className="py-2">Token</th>
                      <th className="py-2">Platform</th>
                      <th className="py-2">Entry</th>
                      <th className="py-2">Amount</th>
                      <th className="py-2">PnL SOL</th>
                      <th className="py-2">PnL %</th>
                      <th className="py-2">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.length === 0 ? (
                      <tr>
                        <td colSpan="7" className="py-8 text-center text-zinc-600">
                          No active positions
                        </td>
                      </tr>
                    ) : (
                      positions.map((pos, idx) => (
                        <tr key={idx} className="border-b border-zinc-800/50 hover:bg-zinc-800/50 transition-colors">
                          <td className="py-2 font-mono font-bold text-[#14F195]">{pos.token}</td>
                          <td className="py-2 font-mono text-xs text-zinc-400">{pos.platform}</td>
                          <td className="py-2 font-mono text-xs">{pos.entry_price?.toExponential(2)}</td>
                          <td className="py-2 font-mono text-xs">{formatSOL(pos.amount_sol)} SOL</td>
                          <td className={`py-2 font-mono font-bold ${pos.pnl_sol >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'}`}>
                            {pos.pnl_sol >= 0 ? '+' : ''}{formatSOL(pos.pnl_sol)}
                          </td>
                          <td className={`py-2 font-mono font-bold ${pos.pnl_percent >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'}`}>
                            {pos.pnl_percent >= 0 ? '+' : ''}{formatPercent(pos.pnl_percent)}%
                          </td>
                          <td className="py-2 font-mono text-xs text-zinc-500">{new Date(pos.entry_time).toLocaleTimeString()}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          {/* Settings & Activity */}
          <div className="col-span-4 space-y-4">
            {/* Settings */}
            <Card className="bg-[#121214] border-zinc-800 rounded-sm p-4">
              <div className="border-b border-zinc-800 pb-3 mb-3 flex justify-between items-center">
                <h2 className="text-lg font-bold" style={{fontFamily: 'Manrope'}}>Settings</h2>
                <Settings className="w-5 h-5 text-zinc-500" />
              </div>
              
              <div className="space-y-3">
                <div>
                  <Label className="text-xs text-zinc-500" style={{fontFamily: 'JetBrains Mono'}}>Amount per Trade (SOL)</Label>
                  <Input
                    data-testid="amount-per-trade-input"
                    type="number"
                    step="0.01"
                    value={config.amount_per_trade}
                    onChange={(e) => setConfig({...config, amount_per_trade: parseFloat(e.target.value)})}
                    disabled={botRunning}
                    className="bg-zinc-950 border-zinc-800 focus:border-[#14F195] focus:ring-0 rounded-sm font-mono text-sm mt-1"
                  />
                </div>

                <div>
                  <Label className="text-xs text-zinc-500" style={{fontFamily: 'JetBrains Mono'}}>Take Profit (%)</Label>
                  <Input
                    data-testid="take-profit-input"
                    type="number"
                    step="1"
                    value={config.take_profit_percent}
                    onChange={(e) => setConfig({...config, take_profit_percent: parseFloat(e.target.value)})}
                    disabled={botRunning}
                    className="bg-zinc-950 border-zinc-800 focus:border-[#14F195] focus:ring-0 rounded-sm font-mono text-sm mt-1"
                  />
                </div>

                <div>
                  <Label className="text-xs text-zinc-500" style={{fontFamily: 'JetBrains Mono'}}>Stop Loss (%)</Label>
                  <Input
                    data-testid="stop-loss-input"
                    type="number"
                    step="1"
                    value={config.stop_loss_percent}
                    onChange={(e) => setConfig({...config, stop_loss_percent: parseFloat(e.target.value)})}
                    disabled={botRunning}
                    className="bg-zinc-950 border-zinc-800 focus:border-[#14F195] focus:ring-0 rounded-sm font-mono text-sm mt-1"
                  />
                </div>

                <div>
                  <Label className="text-xs text-zinc-500" style={{fontFamily: 'JetBrains Mono'}}>Time Exit (minutes)</Label>
                  <Input
                    data-testid="time-exit-input"
                    type="number"
                    step="1"
                    value={config.time_exit_minutes}
                    onChange={(e) => setConfig({...config, time_exit_minutes: parseInt(e.target.value)})}
                    disabled={botRunning}
                    className="bg-zinc-950 border-zinc-800 focus:border-[#14F195] focus:ring-0 rounded-sm font-mono text-sm mt-1"
                  />
                </div>

                <div>
                  <Label className="text-xs text-zinc-500" style={{fontFamily: 'JetBrains Mono'}}>Slippage (%)</Label>
                  <Input
                    data-testid="slippage-input"
                    type="number"
                    step="0.5"
                    value={config.slippage}
                    onChange={(e) => setConfig({...config, slippage: parseFloat(e.target.value)})}
                    disabled={botRunning}
                    className="bg-zinc-950 border-zinc-800 focus:border-[#14F195] focus:ring-0 rounded-sm font-mono text-sm mt-1"
                  />
                </div>
              </div>
            </Card>

            {/* Activity Log */}
            <Card className="bg-[#121214] border-zinc-800 rounded-sm p-4">
              <div className="border-b border-zinc-800 pb-3 mb-3 flex justify-between items-center">
                <h2 className="text-lg font-bold" style={{fontFamily: 'Manrope'}}>Activity Log</h2>
                <Activity className="w-5 h-5 text-zinc-500" />
              </div>
              
              <div className="space-y-2 overflow-auto" style={{maxHeight: '300px'}}>
                {activityLog.length === 0 ? (
                  <p className="text-xs text-zinc-600 text-center py-4">No activity yet</p>
                ) : (
                  activityLog.map((log, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-xs">
                      <span className="text-zinc-600 font-mono">{log.timestamp}</span>
                      <span className={`flex-1 ${
                        log.type === 'success' ? 'text-[#22C55E]' :
                        log.type === 'error' ? 'text-[#EF4444]' :
                        log.type === 'warning' ? 'text-[#EAB308]' :
                        'text-zinc-400'
                      }`}>
                        {log.message}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
