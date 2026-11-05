# 🔗 Configuration Frontend ↔ Backend

## URLs des Services

| Service | URL | Rôle |
|---------|-----|------|
| **Frontend** | `https://platforme-photo-scan.onrender.com/` | Site web utilisateur |
| **Backend API** | `https://photo-scan-api-9o78.onrender.com/api/v1` | API REST Django |

---

## Configuration Requise dans le Frontend

### **1. URL de Base API**

Dans votre fichier de configuration (`config/api.js` ou `src/config.js`) :

```javascript
export const API_BASE_URL = 'https://photo-scan-api-9o78.onrender.com/api/v1';
```

### **2. Variables d'Environnement**

**Fichier `.env.production`** (pour Render) :
```env
VITE_API_URL=https://photo-scan-api-9o78.onrender.com/api/v1
```

**Fichier `.env.development`** (pour développement local) :
```env
VITE_API_URL=http://localhost:8000/api/v1
```

### **3. Utilisation dans le Code**

```javascript
// config/api.js
const API_BASE_URL = import.meta.env.VITE_API_URL;

export async function fetchEvents() {
  const response = await fetch(`${API_BASE_URL}/events/`);
  return await response.json();
}

export async function login(email, password) {
  const response = await fetch(`${API_BASE_URL}/auth/login/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  });
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access);
  return data;
}
```

---

## ✅ Vérifications

### **Test 1 : Backend Accessible**

Ouvrez dans votre navigateur :
```
https://photo-scan-api-9o78.onrender.com/api/v1/events/
```

✅ Vous devez voir du JSON avec la liste des événements

---

### **Test 2 : CORS Fonctionnel**

Dans la console de votre frontend (F12) :

```javascript
fetch('https://photo-scan-api-9o78.onrender.com/api/v1/events/')
  .then(r => r.json())
  .then(d => console.log('✅ API OK:', d))
  .catch(e => console.error('❌ Erreur:', e));
```

✅ Vous devez voir les données sans erreur CORS

---

## 🐛 Problèmes Courants

### **Erreur : "Failed to fetch"**

**Cause** : Backend endormi (plan gratuit Render)  
**Solution** : Attendre 30-60 secondes, le backend se réveille automatiquement

---

### **Erreur CORS**

**Cause** : URL frontend pas autorisée  
**Solution** : Vérifier que `https://platforme-photo-scan.onrender.com` est dans `CORS_ALLOWED_ORIGINS` du backend

---

### **Erreur 401 Unauthorized**

**Cause** : Token JWT manquant ou expiré  
**Solution** : 
```javascript
const token = localStorage.getItem('access_token');
fetch(url, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

---

## 📚 Documentation Complète

Consultez `GUIDE_COMPLET_API.md` pour :
- Tous les endpoints disponibles
- Exemples de code complets
- Gestion des erreurs
- Authentification JWT
- Upload de fichiers
- Et plus...

---

## 🎯 Endpoints Essentiels

### **Publics (Sans Auth)**

| Endpoint | Description |
|----------|-------------|
| `GET /events/` | Liste des événements |
| `GET /events/{slug}/` | Détails d'un événement |
| `POST /auth/login/` | Connexion |
| `POST /participants/` | Inscription participant |

### **Admin (Avec JWT)**

| Endpoint | Description |
|----------|-------------|
| `POST /admin/events/` | Créer un événement |
| `POST /admin/events/{slug}/media/` | Upload photos |
| `GET /admin/stats/` | Statistiques |

### **Participant (Avec Token)**

| Endpoint | Description |
|----------|-------------|
| `POST /participants/{id}/face-reference/` | Upload selfie |
| `GET /events/{slug}/my-photos/` | Mes photos |

---

## ✅ Configuration Validée

- [x] Backend déployé et accessible
- [x] CORS configuré pour `https://platforme-photo-scan.onrender.com`
- [x] Tous les bugs corrigés
- [x] Documentation complète disponible

**Date de validation** : 05/11/2026
