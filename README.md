# 🤖 Bot Trading Crypto - Projet Étudiant

## Vision
Bot d'apprentissage qui trade avec 5€/mois via stratégies validées (DCA, grid).
Utilise Blockscout pour data on-chain et Binance testnet.

## Objectifs
- **Phase 1 (Mois 1-3)** : Bot DCA fonctionnel, backtests positifs
- **Phase 2 (Mois 3-6)** : Live trading 5€, ROI >10%/mois
- **Phase 3 (Mois 6+)** : Scale capital, envisager SaaS

## Stack Technique
- Python 3.11+
- Blockscout MCP (blockchain data)
- ccxt (Binance API)
- pandas/numpy (analyse)
- pytest (tests)

## Installation

```bash
git clone https://github.com/ostrolawzyy-beep/crypto-trading-bot
cd crypto-trading-bot
pip install -r requirements.txt
cp .env.example .env  # Remplis tes clés API
python main.py --mode backtest
```

## Configuration

Édite `config.yaml` pour ajuster:
- Capital initial
- Paires de trading
- Seuils RSI
- Risk management

## Stratégies Implémentées

### 1. DCA Optimisé
Achète BTC/ETH quand:
- RSI < 30 (survente)
- Prix < SMA20 (tendance baissière)

Vend quand:
- RSI > 70 (surachat)

### 2. Grid Trading (Phase 2)
Ordres espacés de 3% pour capturer la volatilité.

## Sécurité

⚠️ **IMPORTANT**:
- Testnet Binance UNIQUEMENT au début
- Stop-loss 2% par trade
- Max 20% capital par position
- Ne jamais commit les clés API (`.env` dans `.gitignore`)

## Structure du Projet

```
crypto-trading-bot/
├── src/
│   ├── blockscout_client.py  # Interface Blockscout MCP
│   ├── strategy.py           # Logique de trading
│   ├── executor.py           # Exécution ordres Binance
│   ├── portfolio.py          # Tracking P&L
│   └── utils.py              # Utilitaires
├── tests/                    # Tests unitaires
├── data/                     # Logs et backtests
├── notebooks/                # Analyses Jupyter
├── config.yaml               # Configuration
├── .env.example              # Template secrets
└── main.py                   # Point d'entrée
```

## Usage

### Mode Backtest
```bash
python main.py --mode backtest
```

### Mode Live (testnet)
```bash
python main.py --mode live
```

## Tests
```bash
pytest tests/ -v
```

## Roadmap

- [x] Setup repo et structure
- [ ] Implémentation DCA strategy
- [ ] Intégration Blockscout MCP
- [ ] Executor Binance testnet
- [ ] Backtesting engine
- [ ] Dashboard monitoring
- [ ] Live trading testnet
- [ ] Grid trading strategy

## Contribuer

1. Fork le projet
2. Crée une branche (`git checkout -b feature/amazing-feature`)
3. Commit tes changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvre une Pull Request

## License

MIT License - voir LICENSE pour détails

## Disclaimer

⚠️ Ce bot est à but éducatif. Le trading de crypto comporte des risques. N'investis que ce que tu peux te permettre de perdre.
