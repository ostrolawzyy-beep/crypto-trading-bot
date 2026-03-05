# 🤖 Crypto Trading Bot - DCA Strategy v0.3.0

**Bot de trading automatique pour apprendre l'algorithmique et générer des petits gains avec 5€/mois.**

## 🎯 Objectifs

- **Apprendre** : Comprendre les indicateurs techniques (RSI, SMA, EMA), backtesting, optimisation
- **Expérimenter** : Tester des stratégies sans risque sur testnet Binance
- **Gagner** : Viser 2-5% de profit mensuel avec capital minimal

---

## ✨ Fonctionnalités

### 📈 Stratégie DCA Optimisée
- **Indicateurs** : RSI (surachat/survente), SMA (moyenne mobile), EMA200 (filtre macro)
- **Risk Management** :
  - 🛑 **Stop-loss** : Coupe pertes à -2%
  - 💰 **Trailing stop** : Sécurise gains à -1.5% du plus haut
  - 🎯 **Kelly Criterion** : Sizing dynamique basé sur historique (optionnel)
- **Simulation réaliste** : Frais Binance (0.1%), slippage (0.05%)

### 🔧 Outils Avancés
- 🔍 **Multi-pair optimizer** : Teste 10 paires simultanément
- ✅ **Out-of-sample validation** : Évite l'overfitting (split 60/40)
- 🚨 **Kill-switch** : Arrêt automatique si perte > 10% ou 5 pertes consécutives
- ⏱️ **Circuit breaker** : Limite à 10 trades/heure max
- 🔁 **Retry logic** : Gestion auto des erreurs réseau

### 📊 Métriques
- **Profit net** (après frais)
- **Win rate** (% trades gagnants)
- **Espérance de gain (EV)** : Gain moyen par trade
- **Sharpe ratio** : Ratio rendement/risque
- **Max drawdown** : Perte max depuis plus haut

---

## 🚀 Installation

### 1️⃣ Prérequis

```bash
# Python 3.9+
python --version

# Git
git --version
```

### 2️⃣ Cloner le repo

```bash
git clone https://github.com/ostrolawzyy-beep/crypto-trading-bot.git
cd crypto-trading-bot
```

### 3️⃣ Créer environnement virtuel

```bash
# Créer venv
python -m venv venv

# Activer
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 4️⃣ Installer dépendances

```bash
pip install -r requirements.txt
```

### 5️⃣ Configuration

```bash
# Copier template
cp .env.example .env

# Éditer avec tes clés Binance TESTNET
nano .env
```

**.env** :
```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_secret_here
```

⚠️ **IMPORTANT** : Utilise uniquement les clés **testnet** au début !
- Testnet API : https://testnet.binance.vision/
- Crée un compte, génère des clés API

---

## 💻 Utilisation

### 🔹 Backtest simple (1 paire)

```bash
# BTC/USDT sur 30 jours
python main.py --mode backtest --pair BTC/USDT --period 30d

# ETH/USDT sur 90 jours
python main.py --mode backtest --pair ETH/USDT --period 90d --debug
```

**Output exemple** :
```
============================================================
RESULTATS BACKTEST - REALISTE (frais + slippage + stops)
============================================================
Capital initial: 5.00 EUR
Capital final: 5.11 EUR
Profit net: +2.23%
Total frais payés: 0.0101 EUR

Nombre de trades: 4 (2 BUY, 2 SELL)
Win rate: 50.0% (1 gagnants, 1 perdants)

=== METRIQUES AVANCEES ===
Espérance de gain (EV): +0.0583 EUR/trade
Gain moyen (winners): +0.1430 EUR
Perte moyenne (losers): -0.0265 EUR
Max Drawdown: -1.36%
Sharpe Ratio: 0.84

=== STOPS & PROTECTIONS ===
Stop-loss déclenchés: 0
Trailing stop déclenchés: 1
Ventes sur signal RSI: 1
============================================================
```

---

### 🔹 Optimizer Multi-Paires

Teste automatiquement 10 paires pour trouver les meilleures :

```bash
# Test standard (paramètres config.yaml)
python optimizer.py --period 30d

# Mode optimisation (cherche meilleurs paramètres RSI)
python optimizer.py --period 90d --optimize

# Paires spécifiques
python optimizer.py --period 30d --pairs BTC/USDT ETH/USDT BNB/USDT
```

**Output exemple** :
```
================================================================================
RESULTATS FINAUX (triés par Sharpe Ratio)
================================================================================

      pair  profit_percent  win_rate  sharpe_ratio  max_drawdown  num_trades  expected_value
  BTC/USDT            2.23      50.0          0.84         -1.36           4          0.0583
  BNB/USDT            4.12      60.0          1.20         -2.10           5          0.0821
 SOL/USDT            1.85      55.0          0.92         -1.80           6          0.0308
  ETH/USDT           -2.91       0.0         -1.29         -2.91           4         -0.0703

============================================================
TOP 3 PAIRES RECOMMANDEES
============================================================

#1: BNB/USDT
  Profit: +4.12%
  Win Rate: 60.0%
  Sharpe: 1.20
  Max DD: -2.10%
  EV: +0.0821 EUR/trade
```

➡️ **Résultat** : Fichier `optimization_results.csv` généré

---

### 🔹 Validation Out-of-Sample

Évite l'overfitting en testant sur données jamais vues :

```bash
# Valide BTC/USDT sur 180 jours (60% train, 40% test)
python validate.py --pair BTC/USDT --period 180d

# Custom split (70% train, 30% test)
python validate.py --pair ETH/USDT --period 180d --train-pct 0.7
```

**Output exemple** :
```
============================================================
COMPARAISON TRAIN vs TEST
============================================================

Metric               Training         Test            Diff
=================================================================
Profit %                 3.45         2.80           -0.65
Win Rate %              55.00        52.00           -3.00
Sharpe Ratio             1.12         0.98           -0.14
Max Drawdown %          -2.30        -2.80           -0.50

============================================================
ANALYSE OVERFITTING
============================================================
[OK] Performance test proche du train (-0.65%)
[OK] Sharpe stable (-0.14)

============================================================
RECOMMANDATION FINALE
============================================================
[+] STRATÉGIE VALIDÉE
    Config recommandée: RSI buy<30, sell>70
    Performance attendue: +2.80% avec Sharpe 0.98
    -> Prêt pour live testnet
```

---

### 🔹 Mode Live (Testnet)

⚠️ **IMPORTANT** : Toujours commencer par testnet !

```bash
# Vérifie config.yaml : testnet: true
python main.py --mode live
```

➡️ Mode live en développement (coming soon)

---

## ⚙️ Configuration

**config.yaml** :

```yaml
strategies:
  dca:
    # Paires à trader
    pairs:
      - "BTC/USDT"
      - "ETH/USDT"
    
    # Indicateurs
    buy_threshold_rsi: 30    # Acheter si RSI < 30 (survente)
    sell_threshold_rsi: 70   # Vendre si RSI > 70 (surachat)
    sma_period: 20           # Période SMA
    
    # Sizing
    trade_amount_percent: 0.5  # 50% du capital par trade
    
    # Frais & Slippage
    maker_fee: 0.001         # 0.1% Binance maker
    taker_fee: 0.001         # 0.1% Binance taker
    slippage: 0.0005         # 0.05% slippage moyen
    
    # Risk Management
    stop_loss_pct: 0.02          # -2% stop loss
    trailing_stop_pct: 0.015     # -1.5% trailing stop
    use_kelly_criterion: false   # Kelly sizing (désactivé)
    kelly_fraction: 0.25         # 25% du Kelly optimal

trading:
  capital_initial: 5.0  # Capital de départ (EUR)
```

---

## 📁 Structure du Projet

```
crypto-trading-bot/
├── src/
│   ├── strategy.py       # Stratégie DCA + indicateurs
│   ├── executor.py       # Exécution ordres Binance
│   └── utils.py          # Utilitaires (logging, config)
├── main.py              # Point d'entrée principal
├── optimizer.py         # Multi-pair optimizer
├── validate.py          # Out-of-sample validation
├── config.yaml          # Configuration
├── requirements.txt     # Dépendances
└── README.md            # Ce fichier
```

---

## 📚 Ressources

### Apprendre
- [Indicateur RSI](https://www.investopedia.com/terms/r/rsi.asp)
- [Dollar Cost Averaging](https://www.investopedia.com/terms/d/dollarcostaveraging.asp)
- [Kelly Criterion](https://en.wikipedia.org/wiki/Kelly_criterion)
- [Sharpe Ratio](https://www.investopedia.com/terms/s/sharperatio.asp)

### Documentation
- [Binance API](https://binance-docs.github.io/apidocs/spot/en/)
- [CCXT Library](https://docs.ccxt.com/)
- [Pandas TA](https://github.com/twopirllc/pandas-ta)

---

## ⚠️ Avertissements

1. **Risque** : Le trading comporte des risques. Ne trade que ce que tu peux te permettre de perdre.
2. **Testnet d'abord** : Toujours tester en testnet avant production.
3. **Pas de garantie** : Performances passées ≠ performances futures.
4. **Éducation** : Ce bot est un outil d'apprentissage, pas un conseil financier.
5. **Kill-switch** : Le bot s'arrête automatiquement si perte > 10%.

---

## 🐛 Débogage

### Erreur de connexion Binance
```bash
# Vérifie tes clés API dans .env
cat .env

# Vérifie testnet activé dans config.yaml
grep testnet config.yaml
```

### Pas assez de données
```bash
# Augmente la période
python main.py --period 90d

# Ou change de paire
python main.py --pair BNB/USDT
```

### Erreur de dépendances
```bash
# Réinstalle proprement
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

---

## 🚀 Prochaines Étapes

- [ ] Mode live fonctionnel avec boucle 1h
- [ ] Dashboard web (Flask) temps réel
- [ ] Support multi-timeframes (1h, 4h, 1d)
- [ ] Intégration Telegram pour alertes
- [ ] Machine Learning pour prédictions
- [ ] Support autres exchanges (Kraken, Coinbase)

---

## 💬 Contact

- GitHub : [@ostrolawzyy-beep](https://github.com/ostrolawzyy-beep)
- Repo : https://github.com/ostrolawzyy-beep/crypto-trading-bot

---

## 📜 Licence

MIT License - Fais-en ce que tu veux ! 🚀

---

**Happy Trading! 💸✨**
