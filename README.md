
# Kubernetes Observability Lab

End-to-end **observability lab** built around a small FastAPI service running on a local Kubernetes cluster (Docker Desktop).  

The project shows how to:

- Containerise a **FastAPI** app and deploy it to **Kubernetes**
- Expose custom **Prometheus metrics** from the app (`/metrics`)
- Scrape those metrics with **Prometheus** via a `ServiceMonitor`
- Build **Grafana dashboards** for traffic and error rates
- Configure **Prometheus alerts** and route them to **Alertmanager**
- Extend with an **EFK logging stack** (Elasticsearch, Fluent Bit, Kibana)


## Architecture Overview

**Platform**

- Kubernetes: Docker Desktop local cluster
- Helm: package manager for Prometheus / Elastic stack

**Application**

- FastAPI service (Python)
- Endpoints:
  - `GET /` – health check / root
  - `GET /api/items` – dummy business endpoint
  - `GET /error` – deliberately returns HTTP 500 (used to trigger alerts)
  - `GET /metrics` – Prometheus text format metrics

**Observability**

           +----------------+
           |  FastAPI app   |
           | (demo service) |
           +--------+-------+
                    |
           /metrics |  HTTP /api/*
                    v
          +---------+-----------------+
          |        Prometheus         |
          | (kube-prometheus-stack)   |
          +----+----------------------+
               |  scrapes
               |
               v
         +-----+---------+       +-----------------+
         |   Grafana     |<----->|  Alertmanager   |
         | Dashboards    |       | (from Prometheus|
         +---------------+       +-----------------+

    Pod logs --> Fluent Bit --> Elasticsearch --> Kibana


## Repository Structure


app/
  Dockerfile              # Build image for demo FastAPI app
  requirements.txt        # Python dependencies
  src/
    main.py               # FastAPI application with /metrics

k8s/
  base/
    namespace.yml         # Namespace: observability-lab
    app-deployment.yml    # Deployment: demo-app
    app-service.yml       # Service: demo-app-service

monitoring/
  kube-prometheus-values.yml      # Values for kube-prometheus-stack Helm chart
  prometheus/
    app-servicemonitor.yml        # ServiceMonitor for demo-app
    app-alert-rules.yml           # PrometheusRule: high error rate alert

logging/                           # Optional EFK logging (advanced / WIP)
  elasticsearch-values.yml
  elasticsearch-simple-values.yml
  fluentbit-values.yml

.gitignore
README.md

## Prerequisites

* **Docker Desktop** with **Kubernetes enabled**
* **kubectl** configured to use the `docker-desktop` context
* **Helm 3**
* Python 3.10+ 

All commands below are running from the project root.


## 1. Build & Push the Application Image

You can use your own Docker Hub username; change `<your-dockerhub-username>` below.

cd app

# Build local image
docker build -t observability-demo-app:v1 .

# Tag for Docker Hub
docker tag observability-demo-app:v1 <your-dockerhub-username>/observability-demo-app:v1

# Push
docker push <your-dockerhub-username>/observability-demo-app:v1

In `k8s/base/app-deployment.yml`, make sure the container image matches what you pushed:

image: <your-dockerhub-username>/observability-demo-app:v1


## 2. Deploy the Demo App to Kubernetes


# Create namespace
kubectl apply -f k8s/base/namespace.yml

# Deploy app and service
kubectl apply -f k8s/base/app-deployment.yml
kubectl apply -f k8s/base/app-service.yml

# Check pods
kubectl get pods -n observability-lab


You should see the `demo-app` pods become `Running`.

To test the service from your machine:

kubectl port-forward svc/demo-app-service -n observability-lab 8080:80

Then in a browser or new terminal:

* `http://localhost:8080/` – root
* `http://localhost:8080/api/items` – sample data
* `http://localhost:8080/metrics` – Prometheus metrics


## 3. Install Prometheus, Grafana & Alertmanager (kube-prometheus-stack)

This project uses the **kube-prometheus-stack** chart.

# Create namespace for monitoring stack
kubectl create namespace monitoring

# Add Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack with custom values
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring \
  -f monitoring/kube-prometheus-values.yml


Wait for pods:


kubectl get pods -n monitoring


## 4. Wire the App to Prometheus (ServiceMonitor)

Apply the Prometheus objects that link your app to the monitoring stack:


kubectl apply -f monitoring/prometheus/app-servicemonitor.yml
kubectl apply -f monitoring/prometheus/app-alert-rules.yml


These do two things:

1. **ServiceMonitor**
   Tells Prometheus to scrape the `demo-app-service` at `/metrics`.

2. **PrometheusRule**
   Defines `DemoAppHighErrorRate` – an alert that fires when the `/error` endpoint has a high error rate over a period (for demo purposes).


## 5. Access Prometheus, Grafana and Alertmanager

### Prometheus UI

kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090


Open `http://localhost:9090`:

* **Status → Targets** → verify the `demo-app` endpoint is **UP**.
* **Graph** tab → query: `demo_app_requests_total`

### Grafana UI

kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80

Default Grafana creds (from chart values) are often `admin / prom-operator`, but check `kube-prometheus-values.yml` if you changed them.

Open `http://localhost:3000` and log in.

The Prometheus data source is pre-configured by the chart.


## 6. Build the Dashboard in Grafana

Inside Grafana:

1. **Create a new dashboard → Add a new panel**

2. Choose **Prometheus** as the data source.

3. Use the query:

   sum(rate(demo_app_requests_total[5m])) by (endpoint)


   * Visualization: **Time series**
   * Title idea: `RPS by endpoint`

4. Add another panel with:

   sum(increase(demo_app_requests_total[10m])) by (endpoint)


   * Title: `Requests in last 10m by endpoint`

Save the dashboard as e.g. **“Demo App – HTTP Overview”**.

You now have live traffic graphs driven by Prometheus metrics from your FastAPI app.


## 7. Trigger & View an Alert

The `app-alert-rules.yml` file defines a simple example alert `DemoAppHighErrorRate`.

1. Generate error traffic:

   # Terminal A
   kubectl port-forward svc/demo-app-service -n observability-lab 8080:80

   # Terminal B
   while true; do curl -s http://localhost:8080/error > /dev/null; sleep 2; done

2. In Prometheus (`http://localhost:9090`) go to **Status → Rules**
   – you should see the `DemoAppHighErrorRate` rule.

3. Under **Alerts**, the alert will first be `Pending` then `Firing`.

4. Access **Alertmanager**:

   kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-alertmanager 9093:9093

   Open `http://localhost:9093` and you’ll see the same alert there.

This demonstrates the full chain:

> Application errors → Prometheus metrics → Alert rule → Alertmanager.


## 8. Optional: EFK Logging Stack (Advanced / WIP)

The `logging/` folder contains Helm values for adding a basic **EFK** stack:

* `logging/elasticsearch-*.yml` – single-node Elasticsearch configs
* `logging/fluentbit-values.yml` – Fluent Bit configuration to ship pod logs into Elasticsearch

These manifests are provided as a starting point and may need adjustments for your environment (Elasticsearch security, TLS, resource limits, etc.).

They are **not required** for the core metrics + alerting lab, but can be used to extend the project with:

* Centralised log storage in Elasticsearch
* Structured logs shipped by Fluent Bit
* Log exploration via Kibana


## 9. Clean-up

To remove all resources from the cluster:

helm uninstall monitoring -n monitoring
kubectl delete namespace monitoring

kubectl delete -f k8s/base/app-service.yml
kubectl delete -f k8s/base/app-deployment.yml
kubectl delete -f k8s/base/namespace.yml


(If you installed any logging components, uninstall those Helm releases too.)


## How This Project Demonstrates DevOps Skills

You can summarise this project on your CV or LinkedIn like this:

* Containerised a FastAPI microservice and deployed it to a local Kubernetes cluster (Docker Desktop) using Deployment and Service manifests.
* Installed and configured the kube-prometheus-stack (Prometheus, Grafana, Alertmanager) via Helm, wiring it to the application using ServiceMonitor and PrometheusRule resources.
* Built Grafana dashboards and alerting rules to monitor HTTP traffic and error rates, demonstrating end-to-end observability and incident detection in a Kubernetes environment.


## License

Feel free to re-use or adapt this lab for your own learning and portfolio.
