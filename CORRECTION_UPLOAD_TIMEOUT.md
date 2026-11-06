# 🔴 Correction Bug Upload Images - Worker Timeout

## 🐛 Problème Identifié

**Symptôme :** `POST /api/v1/admin/events/{slug}/media/` retourne 500 ou "Failed to fetch"

**Logs Render :**
```
[CRITICAL] WORKER TIMEOUT (pid:61)
[ERROR] Worker (pid:61) was sent SIGKILL! Perhaps out of memory?
```

**Cause Racine :**

Le modèle **InsightFace `buffalo_l`** (281 MB) est téléchargé à la **première requête d'upload** :
- Temps de téléchargement : **30-60 secondes**
- Timeout Gunicorn par défaut : **30 secondes** ⚠️
- RAM consommée : **400-500 MB** sur un plan Free avec **512 MB max**

Résultat : Le worker est tué par Gunicorn (timeout) ou par le système (OOM).

---

## ✅ Solutions Appliquées

### 1️⃣ Configuration Gunicorn Optimisée

**Fichier créé :** `photo/gunicorn.conf.py`

Changements :
- **Timeout : 30s → 120s** (2 minutes pour télécharger le modèle)
- **Workers : auto → 1** (économie RAM sur Render Free)
- **Graceful timeout : 120s** (permet de finir les requêtes en cours)

**Utilisation via :** `Procfile` à la racine du projet

```
web: cd photo && gunicorn photo.wsgi:application --config gunicorn.conf.py
```

---

### 2️⃣ Pré-téléchargement du Modèle au Build

**Fichier créé :** `photo/download_insightface_model.py`

**Modification :** `photo/build.sh` 

Le modèle est maintenant téléchargé **pendant le build Render**, pas à la première requête.

Avantages :
- ✅ Premier upload d'image instantané (modèle déjà en cache)
- ✅ Pas de timeout sur la première requête
- ✅ Build plus long (+1-2 min) mais runtime stable

---

### 3️⃣ Architecture du Système de Reconnaissance Faciale

**Comment ça fonctionne :**

1. **Premier appel** à `get_face_app()` :
   - Télécharge `buffalo_l.zip` (281 MB) depuis GitHub
   - Extrait les fichiers `.onnx` dans `/opt/render/.insightface/models/`
   - Charge les modèles en mémoire (détection + reconnaissance)
   - Cache le modèle dans la variable globale `_app`

2. **Appels suivants** :
   - Réutilisation de `_app` en cache (instantané)
   - Pas de re-téléchargement

3. **Redémarrage du serveur Render** :
   - ⚠️ Le cache mémoire (`_app`) est perdu
   - ✅ Les fichiers `.onnx` restent sur disque (pas de re-téléchargement)
   - Premier appel après redémarrage : **rapide** (charge depuis disque)

---

## 🚀 Déploiement des Corrections

### Étape 1 : Commit et Push

```powershell
cd c:\Users\DELL\Projet

git add .
git commit -m "fix: Configuration Gunicorn + pré-téléchargement InsightFace

- Augmentation timeout Gunicorn 30s → 120s
- Pré-téléchargement du modèle buffalo_l au build
- Optimisation workers Gunicorn pour Render Free (512 MB RAM)
- Ajout Procfile pour Render"

git push origin main
```

### Étape 2 : Attendre le Build Render (7-10 minutes)

Le build sera plus long car il télécharge le modèle InsightFace :

```
==> Pré-téléchargement du modèle InsightFace (buffalo_l)...
🔽 Pré-téléchargement du modèle InsightFace buffalo_l...
⚠️  Cela peut prendre 1-2 minutes (téléchargement de ~281 MB)...
download_path: /opt/render/.insightface/models/buffalo_l
Downloading buffalo_l.zip from https://github.com/...
100%|██████████| 281857/281857 [00:18<00:00, 15395.77KB/s]
✅ Modèle InsightFace téléchargé et prêt.
```

### Étape 3 : Tester l'Upload d'Images

**Test 1 : Upload via Postman/Frontend**

```bash
POST https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/nuit-des-entrepreneurs/media/
Authorization: Bearer <TOKEN>
Content-Type: multipart/form-data

# Body: form-data
# Key: "files" (type: File)
# Value: Sélectionner une ou plusieurs images JPG/PNG
```

**Résultat attendu :** 201 Created en 2-5 secondes

**Test 2 : Vérifier les logs Render**

Dashboard → Service → Logs :

```
[INFO] apps.faces.engine Chargement du modèle InsightFace FaceAnalysis(buffalo_l)...
[INFO] apps.faces.engine Modèle InsightFace prêt.
127.0.0.1 - - [06/Nov/2026:01:30:00 +0000] "POST /api/v1/admin/events/.../media/ HTTP/1.1" 201 ...
```

✅ Pas de `WORKER TIMEOUT`  
✅ Pas de `SIGKILL`  
✅ Code 201 au lieu de 500

---

## 📊 Performances Attendues

### Render Free Tier (512 MB RAM)

| Opération | Avant | Après |
|-----------|-------|-------|
| Premier upload (build) | ❌ Timeout 30s | ✅ 2-5s (modèle pré-chargé) |
| Uploads suivants | ❌ Timeout 30s | ✅ 2-5s |
| Redémarrage serveur | ❌ Timeout 30s | ✅ 2-3s (charge depuis disque) |
| RAM utilisée | 400-500 MB | 400-500 MB |
| Risque OOM | 🔴 Élevé | 🟡 Moyen |

### Limitations Render Free Tier

- **1 worker seulement** (512 MB RAM insuffisante pour 2+ workers)
- **Uploads séquentiels** (pas de parallélisation)
- **Risque OOM** si plusieurs uploads simultanés
- **Service inactif après 15 min** (cold start)

---

## 🎯 Recommandations

### Option 1 : Render Starter Plan ($7/mois)

- **2 GB RAM** → Permet 2-3 workers Gunicorn
- **Uploads parallèles** possibles
- **Pas de cold start**
- **Meilleure stabilité**

### Option 2 : Upload Asynchrone avec Celery (Complexe)

- Déplacer le traitement d'images vers **Celery workers**
- Requiert **Redis** ou **RabbitMQ** (service externe)
- Frontend reçoit 202 Accepted immédiatement
- Traitement en arrière-plan

### Option 3 : Service Externe (Recommandé Long Terme)

- **AWS Lambda** avec conteneur InsightFace
- **Google Cloud Run** avec auto-scaling
- **Cloudflare Workers AI** (facial recognition managed)

---

## ✅ Checklist de Validation

Après déploiement :

- [ ] Build Render réussit avec téléchargement InsightFace
- [ ] Logs montrent "Modèle InsightFace téléchargé et prêt"
- [ ] Premier upload d'image retourne 201 (pas 500)
- [ ] Uploads suivants fonctionnent
- [ ] Pas de `WORKER TIMEOUT` dans les logs
- [ ] Pas de `SIGKILL` dans les logs
- [ ] RAM stable < 500 MB dans Render metrics

---

## 🆘 Dépannage

### Si le build échoue

```bash
# Render Shell
cd photo
python download_insightface_model.py
```

### Si timeout persiste

Vérifier que Render utilise bien `Procfile` :
- Dashboard → Service → Settings → **Start Command** doit être vide
- Render détecte automatiquement `Procfile` à la racine

### Si OOM persiste

1. **Réduire det_size** dans `engine.py` :
   ```python
   _app.prepare(ctx_id=-1, det_size=(320, 320))  # au lieu de (640, 640)
   ```

2. **Désactiver seed_data** dans `build.sh` (économie RAM au build)

3. **Upgrade vers Render Starter** ($7/mois, 2 GB RAM)

---

## 📝 Fichiers Modifiés

1. ✅ `photo/gunicorn.conf.py` - Configuration Gunicorn
2. ✅ `Procfile` - Commande de démarrage Render
3. ✅ `photo/build.sh` - Script de build avec pré-téléchargement
4. ✅ `photo/download_insightface_model.py` - Script de pré-téléchargement

---

**Date :** 2026-11-06  
**Version :** 1.0  
**Status :** ✅ Correction appliquée, en attente de déploiement
