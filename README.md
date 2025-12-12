# Kubernetes Observability Lab

Small FastAPI application deployed to a local Kubernetes cluster (Docker Desktop) with basic observability:

- **Metrics:** Prometheus scraping `/metrics` via ServiceMonitor
- **Dashboards:** Grafana time-series panels for requests per endpoint
- **Alerting:** PrometheusRule + Alertmanager for high error rate on `/error` endpoint
- **Platform:** Docker Desktop Kubernetes, Helm, kube-prometheus-stack

## Tech stack

- FastAPI, Python
- Docker
- Kubernetes (Docker Desktop)
- Prometheus, Grafana, Alertmanager (kube-prometheus-stack Helm chart)

## High-level architecture

FastAPI app → `/metrics` → Prometheus → Grafana dashboards  
FastAPI `/error` traffic → Prometheus alert → Alertmanager

## How to run (short version)

1. Enable Kubernetes in Docker Desktop.
2. Deploy the app manifests from `k8s/`.
3. Install kube-prometheus-stack with the values in `monitoring/`.
4. Port-forward Grafana and Prometheus services and open the dashboards.

