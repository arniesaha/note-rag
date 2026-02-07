# note-rag Helm Chart

Deploy note-rag on Kubernetes with Helm.

## Prerequisites

- Kubernetes cluster (k3s, minikube, etc.)
- Helm 3.x
- Traefik ingress controller (for IngressRoute)
- Local Docker image: `note-rag-api:latest`

## Build the Docker Image

```bash
cd ../services
docker build -t note-rag-api:latest -f api/Dockerfile api/
```

## Install

```bash
# From the helm directory
helm install note-rag . -n apps --create-namespace

# Or from project root
helm install note-rag ./helm -n apps --create-namespace
```

## Upgrade

```bash
helm upgrade note-rag . -n apps
```

## Uninstall

```bash
helm uninstall note-rag -n apps
```

## Configuration

Key values in `values.yaml`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Docker image name | `note-rag-api` |
| `image.tag` | Image tag | `latest` |
| `ingress.host` | Hostname for ingress | `kg.arnabsaha.com` |
| `volumes.obsidian` | Host path to Obsidian vault | `/home/Arnab/clawd/projects/note-rag/obsidian` |
| `volumes.lancedb` | Host path to LanceDB storage | `/home/Arnab/clawd/projects/note-rag/lancedb` |
| `ollama.enabled` | Deploy Ollama sidecar | `true` |

## Post-Install

Pull required Ollama models:

```bash
kubectl exec -it deploy/note-rag-ollama -n apps -- ollama pull nomic-embed-text
kubectl exec -it deploy/note-rag-ollama -n apps -- ollama pull qwen2.5:0.5b
```
