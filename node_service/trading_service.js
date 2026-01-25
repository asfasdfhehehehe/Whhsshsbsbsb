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

// Default Jito tip in SOL
const DEFAULT_JITO_TIP = 0.001;

app.post('/api/node/trade', async (req, res) => {
  try {
    const { direction, mint, amount, slippage, privateKey, platform, poolAddress, jitoTip } = req.body;

    if (!privateKey) {
      return res.status(400).json({ error: 'Private key is required' });
    }

    // Create wallet from private key
    const wallet = Keypair.fromSecretKey(bs58.decode(privateKey));

    // Determine market from platform code
    const market = DEX_PLATFORMS[platform] || 'PUMP_FUN';

    // Use provided Jito tip or default
    const tip = jitoTip !== undefined ? parseFloat(jitoTip) : DEFAULT_JITO_TIP;

    const tradeParams = {
      market,
      wallet,
      mint,
      amount: parseFloat(amount),
      slippage: parseFloat(slippage),
      sender: 'JITO',
      jitoTip: tip,  // Add Jito tip amount
      skipSimulation: false,
      skipConfirmation: false
    };

    if (poolAddress) {
      tradeParams.poolAddress = poolAddress;
    }

    console.log(`Executing ${direction} trade for ${mint} on ${market} with Jito tip: ${tip} SOL`);

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
    const { tokens, privateKey, amount, slippage, jitoTip } = req.body;

    if (!privateKey || !tokens || tokens.length === 0) {
      return res.status(400).json({ error: 'Invalid request' });
    }

    const wallet = Keypair.fromSecretKey(bs58.decode(privateKey));
    const results = [];

    // Use provided Jito tip or default
    const tip = jitoTip !== undefined ? parseFloat(jitoTip) : DEFAULT_JITO_TIP;

    // Process up to 2 tokens
    const tokensToProcess = tokens.slice(0, 2);

    for (const token of tokensToProcess) {
      try {
        const market = DEX_PLATFORMS[token.platform] || 'PUMP_FUN';
        console.log(`Batch buying ${token.mint} on ${market} with Jito tip: ${tip} SOL`);
        
        const signature = await trader.buy({
          market,
          wallet,
          mint: token.mint,
          amount: parseFloat(amount),
          slippage: parseFloat(slippage),
          sender: 'JITO',
          jitoTip: tip,  // Add Jito tip amount
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

// Get real slippage estimation for paper trading
// Since solana-trade doesn't expose quote methods, we simulate the trade
// without sending to estimate actual slippage
app.post('/api/node/get-slippage', async (req, res) => {
  try {
    const { mint, amount, direction, slippage, platform } = req.body;

    const market = DEX_PLATFORMS[platform] || 'PUMP_FUN';
    
    // For paper trading slippage estimation, we use Jupiter API as alternative
    // Jupiter aggregates quotes from multiple DEXs including Meteora
    try {
      const jupiterApiUrl = 'https://quote-api.jup.ag/v6/quote';
      const SOL_MINT = 'So11111111111111111111111111111111111111112';
      
      // Determine input/output for Jupiter API
      const inputMint = direction === 'buy' ? SOL_MINT : mint;
      const outputMint = direction === 'buy' ? mint : SOL_MINT;
      
      // Convert amount to lamports/smallest unit
      const amountInSmallestUnit = direction === 'buy' 
        ? Math.floor(parseFloat(amount) * 1e9) // SOL to lamports
        : Math.floor(parseFloat(amount)); // Token amount as-is
      
      // Query Jupiter for quote
      const quoteUrl = `${jupiterApiUrl}?inputMint=${inputMint}&outputMint=${outputMint}&amount=${amountInSmallestUnit}&slippageBps=${parseFloat(slippage) * 100}`;
      
      const response = await fetch(quoteUrl);
      if (response.ok) {
        const quoteData = await response.json();
        
        // Jupiter returns priceImpactPct
        if (quoteData.priceImpactPct) {
          const actualSlippage = Math.abs(parseFloat(quoteData.priceImpactPct));
          console.log(`Real slippage for ${mint} (via Jupiter): ${actualSlippage}%`);
          
          return res.json({
            success: true,
            slippage: actualSlippage,
            source: 'jupiter',
            quote: quoteData
          });
        }
      }
    } catch (jupiterError) {
      console.log('Jupiter API error:', jupiterError.message);
      // Fall through to default
    }

    // Fallback: return configured slippage with small randomization for realism
    // Real slippage varies, so we add +/- 20% variance to configured slippage
    const baseSlippage = parseFloat(slippage);
    const variance = baseSlippage * 0.2; // 20% variance
    const randomFactor = (Math.random() * 2 - 1) * variance; // -variance to +variance
    const estimatedSlippage = Math.max(0.1, baseSlippage + randomFactor);
    
    console.log(`Using estimated slippage: ${estimatedSlippage.toFixed(2)}% (configured: ${baseSlippage}%)`);
    res.json({
      success: false,
      slippage: estimatedSlippage,
      source: 'estimated',
      message: 'Using estimated slippage with variance'
    });

  } catch (error) {
    console.error('Slippage query error:', error);
    res.status(500).json({ 
      error: error.message,
      slippage: req.body.slippage || 5,
      success: false
    });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

const PORT = 8002;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Trading service running on port ${PORT}`);
});
