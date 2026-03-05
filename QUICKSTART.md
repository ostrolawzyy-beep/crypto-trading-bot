# ⚡ Quickstart Guide

**5 minutes pour lancer ton premier backtest !**

---

## 🚀 Installation Express

```bash
# Clone
git clone https://github.com/ostrolawzyy-beep/crypto-trading-bot.git
cd crypto-trading-bot

# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Config (optionnel pour backtest)
cp .env.example .env
```

---

## 🎯 Tests Rapides

### 1️⃣ Backtest Simple (30 secondes)

```bash
python main.py --mode backtest --pair BTC/USDT --period 30d
```

**Résultat attendu** :
```
Profit net: +2.23%
Win rate: 50.0%
Sharpe: 0.84
Trailing stop déclenchés: 1 ✅
```

---

### 2️⃣ Trouver la Meilleure Paire (2 minutes)

```bash
python optimizer.py --period 30d
```

**Résultat attendu** :
```
TOP 3 PAIRES RECOMMANDEES
#1: BNB/USDT   -> +4.12% (Sharpe 1.20)
#2: BTC/USDT   -> +2.23% (Sharpe 0.84)
#3: SOL/USDT   -> +1.85% (Sharpe 0.92)

Paires PERDANTES: ETH/USDT (-2.91%) ❌
```

➡️ **Action** : Trade BNB/USDT avec ces paramètres !

---

### 3️⃣ Valider (Pas d'Overfitting) (3 minutes)

```bash
python validate.py --pair BNB/USDT --period 180d
```

**Résultat attendu** :
```
COMPARAISON TRAIN vs TEST
Profit: 4.12% (train) -> 3.80% (test)  [-0.32%] ✅
Sharpe: 1.20 (train) -> 1.10 (test)    [-0.10] ✅

RECOMMANDATION: [+] STRATÉGIE VALIDÉE
-> Prêt pour live testnet
```

---

## 🔧 Commandes Utiles

### Tester une paire spécifique
```bash
python main.py --pair ETH/USDT --period 90d --debug
```

### Optimiser paramètres RSI
```bash
python optimizer.py --period 90d --optimize --pairs BTC/USDT ETH/USDT
```

### Comparer plusieurs périodes
```bash
# 30 jours
python main.py --pair BTC/USDT --period 30d

# 90 jours
python main.py --pair BTC/USDT --period 90d

# Maximum (1000 bougies = ~41 jours)
python main.py --pair BTC/USDT --period 41d
```

---

## 📊 Interpréter les Résultats

### Métriques Clés

| Métrique | Bon | Moyen | Mauvais |
|----------|-----|-------|--------|
| **Profit** | > 3% | 1-3% | < 0% |
| **Win Rate** | > 55% | 45-55% | < 40% |
| **Sharpe** | > 1.0 | 0.5-1.0 | < 0 |
| **Max DD** | < 3% | 3-7% | > 10% |
| **EV** | > 0.05 | 0.01-0.05 | < 0 |

### Stops

- **Stop-loss déclenché** : Trade perdant coupé à -2% ✅
  - Si trop fréquent (> 30%) : Mauvais points d'entrée RSI
  
- **Trailing stop déclenché** : Gain sécurisé automatiquement ✅
  - Si jamais déclenché : Prix n'a jamais monté assez

---

## ⚠️ Problèmes Courants

### Erreur "Pas assez de données"
```bash
# Solution : Réduis la période
python main.py --period 30d
```

### Toutes les paires sont perdantes
```bash
# Solution : Change la période (marché était baissier)
python optimizer.py --period 90d
```

### Kill-switch activé
```
🛑 KILL-SWITCH ACTIVÉ: Perte > 10%
```
➡️ **Normal** : C'est une protection ! Change de stratégie ou de paire.

---

## 🎯 Prochaine Étape : Live Testnet

### 1. Crée un compte testnet
https://testnet.binance.vision/

### 2. Génère des clés API
- Va dans Account > API Management
- Crée une clé API
- **COPIE** la clé et le secret

### 3. Configure .env
```bash
nano .env
```

```env
BINANCE_API_KEY=ta_cle_testnet_ici
BINANCE_API_SECRET=ton_secret_testnet_ici
```

### 4. Vérifie config.yaml
```yaml
exchanges:
  binance:
    testnet: true  # ✅ IMPORTANT
```

### 5. Lance en mode live (coming soon)
```bash
python main.py --mode live
```

---

## 📚 Ressources

- **README complet** : [README.md](README.md)
- **Code source** : `src/strategy.py`, `src/executor.py`
- **Config** : `config.yaml`

---

**Questions ? Ouvre une issue sur GitHub ! 🚀**
