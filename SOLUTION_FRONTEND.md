# ✅ SOLUTION : Connexion Frontend → Backend

## 🔑 Identifiants Admin (Créés Automatiquement)

```
Email    : admin@clovis-dev.bf
Password : adminpassword123
```

Ces identifiants sont créés automatiquement lors du déploiement sur Render !

---

## 🚀 Code Frontend Minimal (React/TypeScript)

### **1. Service d'Authentification**

```typescript
// services/api.ts
const API_URL = "https://photo-scan-api-9o78.onrender.com/api/v1";

// Fonction de connexion
export async function login(email: string, password: string) {
  const response = await fetch(`${API_URL}/auth/login/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new Error("Échec de connexion");
  }

  const data = await response.json();
  
  // Sauvegarder le token
  localStorage.setItem("access_token", data.access);
  localStorage.setItem("refresh_token", data.refresh);
  
  return data;
}

// Récupérer le token
export function getToken() {
  return localStorage.getItem("access_token");
}

// Créer un événement
export async function createEvent(eventData: any) {
  const token = getToken();
  
  if (!token) {
    throw new Error("Non authentifié");
  }

  const response = await fetch(`${API_URL}/admin/events/`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(eventData),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(JSON.stringify(error));
  }

  return await response.json();
}

// Récupérer les événements
export async function getEvents() {
  const response = await fetch(`${API_URL}/events/`);
  return await response.json();
}
```

---

### **2. Composant de Connexion**

```tsx
// components/Login.tsx
import { useState } from "react";
import { login } from "../services/api";

export function Login({ onSuccess }: { onSuccess: () => void }) {
  const [email, setEmail] = useState("admin@clovis-dev.bf");
  const [password, setPassword] = useState("adminpassword123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await login(email, password);
      alert("✅ Connexion réussie !");
      onSuccess();
    } catch (err: any) {
      setError("❌ " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "400px", margin: "50px auto", padding: "20px" }}>
      <h2>🔐 Connexion Admin</h2>
      
      {error && (
        <div style={{ color: "red", padding: "10px", background: "#ffebee", marginBottom: "10px" }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "15px" }}>
          <label style={{ display: "block", marginBottom: "5px" }}>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: "100%", padding: "8px" }}
            required
          />
        </div>

        <div style={{ marginBottom: "15px" }}>
          <label style={{ display: "block", marginBottom: "5px" }}>Mot de passe</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: "100%", padding: "8px" }}
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "10px",
            background: "#4CAF50",
            color: "white",
            border: "none",
            cursor: "pointer"
          }}
        >
          {loading ? "Connexion..." : "Se connecter"}
        </button>
      </form>
    </div>
  );
}
```

---

### **3. Composant de Création d'Événement**

```tsx
// components/CreateEvent.tsx
import { useState } from "react";
import { createEvent } from "../services/api";

export function CreateEvent() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const formData = new FormData(e.currentTarget);
    
    const eventData = {
      slug: formData.get("slug"),
      name: formData.get("name"),
      tagline: formData.get("tagline"),
      description: formData.get("description"),
      city: formData.get("city"),
      venue: formData.get("venue"),
      date: formData.get("date"),
      status: "traitement",
      organizer_name: formData.get("organizer_name"),
      organizer_phone: formData.get("organizer_phone"),
      highlights: []
    };

    try {
      const result = await createEvent(eventData);
      alert(`✅ Événement créé : ${result.name}`);
      e.currentTarget.reset();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "600px", margin: "50px auto", padding: "20px" }}>
      <h2>➕ Créer un Événement</h2>

      {error && (
        <div style={{ color: "red", padding: "10px", background: "#ffebee", marginBottom: "10px" }}>
          ❌ {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "15px" }}>
          <label>Slug (URL, sans espaces)</label>
          <input
            name="slug"
            placeholder="mariage-aminata-2026"
            required
            style={{ width: "100%", padding: "8px" }}
          />
        </div>

        <div style={{ marginBottom: "15px" }}>
          <label>Nom de l'événement</label>
          <input
            name="name"
            placeholder="Mariage d'Aminata"
            required
            style={{ width: "100%", padding: "8px" }}
          />
        </div>

        <div style={{ marginBottom: "15px" }}>
          <label>Slogan</label>
          <input
            name="tagline"
            placeholder="Une union mémorable"
            required
            style={{ width: "100%", padding: "8px" }}
          />
        </div>

        <div style={{ marginBottom: "15px" }}>
          <label>Description</label>
          <textarea
            name="description"
            placeholder="Description de l'événement"
            required
            style={{ width: "100%", padding: "8px", minHeight: "80px" }}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px", marginBottom: "15px" }}>
          <div>
            <label>Ville</label>
            <input
              name="city"
              placeholder="Ouagadougou"
              required
              style={{ width: "100%", padding: "8px" }}
            />
          </div>
          <div>
            <label>Lieu</label>
            <input
              name="venue"
              placeholder="Hôtel Azalaï"
              required
              style={{ width: "100%", padding: "8px" }}
            />
          </div>
        </div>

        <div style={{ marginBottom: "15px" }}>
          <label>Date</label>
          <input
            name="date"
            type="date"
            required
            style={{ width: "100%", padding: "8px" }}
          />
        </div>

        <div style={{ marginBottom: "15px" }}>
          <label>Nom organisateur</label>
          <input
            name="organizer_name"
            placeholder="Tanou Events"
            required
            style={{ width: "100%", padding: "8px" }}
          />
        </div>

        <div style={{ marginBottom: "15px" }}>
          <label>Téléphone organisateur</label>
          <input
            name="organizer_phone"
            placeholder="+22670123456"
            style={{ width: "100%", padding: "8px" }}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "12px",
            background: "#2196F3",
            color: "white",
            border: "none",
            cursor: "pointer",
            fontSize: "16px"
          }}
        >
          {loading ? "Création..." : "Créer l'événement"}
        </button>
      </form>
    </div>
  );
}
```

---

### **4. App Principal**

```tsx
// App.tsx
import { useState, useEffect } from "react";
import { Login } from "./components/Login";
import { CreateEvent } from "./components/CreateEvent";
import { getToken } from "./services/api";

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Vérifier si un token existe au chargement
    const token = getToken();
    setIsAuthenticated(!!token);
  }, []);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return <Login onSuccess={handleLoginSuccess} />;
  }

  return (
    <div>
      <div style={{ padding: "20px", background: "#f5f5f5", textAlign: "right" }}>
        <button
          onClick={handleLogout}
          style={{
            padding: "8px 16px",
            background: "#f44336",
            color: "white",
            border: "none",
            cursor: "pointer"
          }}
        >
          🚪 Déconnexion
        </button>
      </div>
      
      <CreateEvent />
    </div>
  );
}

export default App;
```

---

## 🧪 Test Rapide (Console Navigateur)

Ouvrez la console (F12) et collez :

```javascript
// 1. Se connecter
fetch('https://photo-scan-api-9o78.onrender.com/api/v1/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'admin@clovis-dev.bf',
    password: 'adminpassword123'
  })
})
.then(r => r.json())
.then(data => {
  console.log('✅ Token:', data.access);
  localStorage.setItem('token', data.access);
});

// 2. Créer un événement (après avoir le token)
const token = localStorage.getItem('token');
fetch('https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    slug: 'mon-test-' + Date.now(),
    name: 'Test Event',
    tagline: 'Test',
    description: 'Description test',
    city: 'Ouaga',
    venue: 'Hotel',
    date: '2026-12-31',
    status: 'traitement',
    organizer_name: 'Test Org'
  })
})
.then(r => r.json())
.then(data => console.log('✅ Événement créé:', data));
```

---

## ✅ Résumé

1. **Votre backend fonctionne parfaitement** ✅
2. **Un compte admin existe** : `admin@clovis-dev.bf` / `adminpassword123` ✅
3. **La création d'événement fonctionne** ✅
4. **Le problème était uniquement l'authentification** ✅

Utilisez le code ci-dessus dans votre frontend et tout fonctionnera ! 🚀
