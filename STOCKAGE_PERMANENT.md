# Stockage permanent et indexation des photos

Les photos, miniatures, logos et couvertures peuvent être stockés dans Cloudflare R2.
Le stockage local reste utilisé en développement tant que les variables R2 ne sont pas
configurées. R2 est un stockage objet compatible avec l'API S3, distinct du disque
éphémère de Render.

## Configuration du bucket R2

1. Créer un bucket R2, puis un jeton API avec les droits de lecture et d'écriture sur ce bucket.
2. Activer l'accès public via un domaine R2 `r2.dev` ou un domaine personnalisé.
   `R2_PUBLIC_DOMAIN` doit être le nom d'hôte public, sans `https://` ni slash final.
3. Ajouter ces variables dans **Render → Environment** :

```env
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=photo-scan-media
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_PUBLIC_DOMAIN=<domaine-public-du-bucket>
```

Le backend refuse de démarrer si une partie seulement de la configuration R2 est fournie.
Ne pas placer les clés dans Git. Après redéploiement, vérifier qu'une nouvelle photo et sa
miniature ont des URL sur le domaine public R2 et restent accessibles après un redéploiement.

`django-storages` et son client S3 sont déjà installés par `photo/requirements.txt`;
la sélection R2 se fait dans `photo/photo/settings.py`. Aucun changement de schéma de base
n'est nécessaire.

## Worker d'indexation faciale

L'upload enregistre la photo et la miniature, puis met l'extraction faciale en file Celery.
Le worker lit les fichiers via l'API de stockage Django, ce qui fonctionne aussi avec R2
(il ne dépend pas de `file.path` sur le disque local).

Dans Render, créer un service **Background Worker** utilisant le même dépôt et le même
environnement que l'API :

- Build command : `cd photo && pip install -r requirements.txt`
- Start command : `cd photo && celery -A photo.celery:app worker --loglevel=INFO --concurrency=1`
- Variables : reprendre `DATABASE_URL`, les variables Django, toutes les variables R2
  ci-dessus et `CELERY_BROKER_URL` pointant vers le Redis utilisé par Celery.

Le worker doit être un service distinct du serveur web. InsightFace consomme beaucoup de
mémoire; vérifier la mémoire du worker sur Render et augmenter son plan si nécessaire. Si
Redis ou le worker est indisponible, la photo est conservée et la réponse d'upload indique
explicitement que l'indexation n'a pas été mise en file (`indexing: unavailable`).

## Médias déjà envoyés

Le changement de backend ne copie pas automatiquement les fichiers existants. Les fichiers
qui sont encore présents sur un disque Render peuvent être migrés avant de le remplacer; les
fichiers déjà supprimés par Render ne peuvent pas être reconstruits à partir des seules lignes
de base de données. Ils doivent être récupérés depuis les originaux, une sauvegarde ou renvoyés.
