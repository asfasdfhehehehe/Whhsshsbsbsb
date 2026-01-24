const { SolanaTrade } = require('solana-trade');
const { Keypair, PublicKey } = require('@solana/web3.js');
const bs58 = require('bs58');
const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const RPC_URL = process.env.RPC_URL || 'https://api.mainnet-beta.solana.com';
const trader = new SolanaTrade(RPC_URL);

// DEX platform mapping based on response format
const DEX_PLATFORMS = {
  '8': 'METEORA_DAMM_V2',
  '1': 'PUMP_FUN',
  '2': 'RAYDIUM_AMM',
  '3': 'RAYDIUM_CLMM',
  '4': 'RAYDIUM_CPMM'
};

app.post('/api/node/trade', async (req, res) => {
  try {
    const { direction, mint, amount, slippage, privateKey, platform, poolAddress } = req.body;

    if (!privateKey) {
      return res.status(400).json({ error: 'Private key is required' });
    }

    // Create wallet from private key
    const wallet = Keypair.fromSecretKey(bs58.decode(privateKey));

    // Determine market from platform code
    const market = DEX_PLATFORMS[platform] || 'PUMP_FUN';

    const tradeParams = {
      market,
      wallet,
      mint,
      amount: parseFloat(amount),
      slippage: parseFloat(slippage),
      sender: 'JITO',
      skipSimulation: false,
      skipConfirmation: false
    };

    if (poolAddress) {
      tradeParams.poolAddress = poolAddress;
    }

    let signature;
    if (direction === 'buy') {
      signature = await trader.buy(tradeParams);
    } else {
      signature = await trader.sell(tradeParams);
    }

    res.json({ signature, success: true });
  } catch (error) {
    console.error('Trade error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/node/batch-trade', async (req, res) => {
  try {
    const { tokens, privateKey, amount, slippage } = req.body;

    if (!privateKey || !tokens || tokens.length === 0) {
      return res.status(400).json({ error: 'Invalid request' });
    }

    const wallet = Keypair.fromSecretKey(bs58.decode(privateKey));
    const results = [];

    // Process up to 2 tokens
    const tokensToProcess = tokens.slice(0, 2);

    for (const token of tokensToProcess) {
      try {
        const market = DEX_PLATFORMS[token.platform] || 'PUMP_FUN';
        const signature = await trader.buy({
          market,
          wallet,
          mint: token.mint,
          amount: parseFloat(amount),
          slippage: parseFloat(slippage),
          sender: 'JITO',
          skipSimulation: false
        });

        results.push({ mint: token.mint, signature, success: true });
      } catch (error) {
        results.push({ mint: token.mint, error: error.message, success: false });
      }
    }

    res.json({ results });
  } catch (error) {
    console.error('Batch trade error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

const PORT = 8002;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Trading service running on port ${PORT}`);
});
