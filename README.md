# 🚀 DevSecOps Platform — Ecommerce Microservices on AWS EKS

[![CI](https://github.com/rasika-08061998/ecommerce-devsecops/actions/workflows/ci.yml/badge.svg)](https://github.com/rasika-08061998/ecommerce-devsecops/actions/workflows/ci.yml)
![AWS](https://img.shields.io/badge/AWS-EKS%20%7C%20ECR%20%7C%20VPC-orange)
![Kubernetes](https://img.shields.io/badge/Kubernetes-v1.30-blue)
![Terraform](https://img.shields.io/badge/Terraform-v1.7-purple)
![ArgoCD](https://img.shields.io/badge/ArgoCD-v3.4-red)

A production-grade **DevSecOps platform** built from scratch on AWS demonstrating end-to-end CI/CD, GitOps, container security, infrastructure as code, and AI-powered monitoring automation.

---

## 🏗️ Architecture

Developer → GitHub → GitHub Actions CI → Amazon ECR
↓
ArgoCD (GitOps)
↓
Amazon EKS (Kubernetes)
┌─────────────────────┐
│  api-gateway :8000  │
│  user-service :8001 │
│  product-svc  :8002 │
│  order-svc    :8003 │
│  payment-svc  :8004 │
│  frontend     :80   │
└─────────────────────┘
↓
Prometheus + Grafana

---

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| Cloud | Amazon Web Services (ap-south-1) |
| Kubernetes | Amazon EKS v1.30 |
| Container Registry | Amazon ECR (6 repositories) |
| Infrastructure as Code | Terraform v1.7 (modular) |
| CI Pipeline | GitHub Actions + OIDC (no IAM keys) |
| CD Pipeline | ArgoCD v3.4 (GitOps) |
| Package Manager | Helm v3.20 |
| Monitoring | Prometheus + Grafana (kube-prometheus-stack) |
| Security Scanning | Trivy (CVE detection) |
| Backend | FastAPI + Python 3.12 |
| Database | PostgreSQL 16 (per-service) |
| Automation | Python AI Scripts (4 scripts) |

---

## 📁 Project Structure
ecommerce-devsecops/
├── .github/workflows/ci.yml     ← GitHub Actions CI pipeline
├── terraform/                   ← Infrastructure as Code
│   ├── provider.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── backend.tf
│   ├── main.tf
│   └── modules/
│       ├── vpc/                 ← VPC, Subnets, IGW, NAT Gateway
│       ├── ecr/                 ← 6 ECR repositories
│       ├── eks/                 ← EKS cluster + node group + OIDC
│       └── iam/                 ← GitHub Actions OIDC role
├── services/                    ← Microservices source code
│   ├── api-gateway/
│   ├── user-service/
│   ├── product-service/
│   ├── order-service/
│   ├── payment-service/
│   └── frontend/
├── helm/ecommerce/              ← Helm chart for all services
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── argocd/applications/         ← ArgoCD Application manifest
├── ai-scripts/                  ← Python DevSecOps automation
│   ├── auto_healer.py
│   ├── log_analyzer.py
│   ├── cost_monitor.py
│   ├── security_scanner.py
│   └── run_all.py
└── .gitignore

---

## 🚀 Quick Start

### Prerequisites
```bash
aws --version        # AWS CLI configured
terraform --version  # >= 1.7.0
kubectl version      # >= 1.28
helm version         # >= 3.0
```

### Step 1 — Create S3 Backend
```bash
aws s3api create-bucket \
  --bucket ecommerce-tfstate-528757804354 \
  --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1

aws s3api put-bucket-versioning \
  --bucket ecommerce-tfstate-528757804354 \
  --versioning-configuration Status=Enabled
```

### Step 2 — Deploy Infrastructure
```bash
cd terraform
terraform init
terraform validate
terraform plan
terraform apply
```
> ⏱️ Takes 25-35 minutes (EKS cluster creation)

### Step 3 — Configure kubectl
```bash
aws eks update-kubeconfig \
  --name ecommerce-dev-cluster \
  --region ap-south-1

kubectl get nodes
```

### Step 4 — Install ArgoCD
```bash
kubectl create namespace argocd

kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Get admin password
kubectl get secret argocd-initial-admin-secret \
  -n argocd \
  -o jsonpath="{.data.password}" | base64 -d
```

### Step 5 — Deploy Application
```bash
kubectl create namespace ecommerce
kubectl apply -f argocd/applications/ecommerce.yaml
```

### Step 6 — Install Monitoring
```bash
helm repo add prometheus-community \
  https://prometheus-community.github.io/helm-charts

helm install monitoring \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.adminPassword=DevSecOps@2026 \
  --set grafana.service.type=LoadBalancer
```

### Step 7 — Run AI Scripts
```bash
pip install -r ai-scripts/requirements.txt
python3 ai-scripts/run_all.py
```

---

## 🔒 Security

### OIDC — No IAM Access Keys
GitHub Actions requests OIDC token
↓
AWS verifies token signature
↓
Assumes IAM role (1 hour temp credentials)
↓
Pushes to ECR + deploys to EKS
↓
Token expires automatically

### Trivy Security Scanning
- Scans every Docker image before push to ECR
- Detects CRITICAL and HIGH CVEs
- Found and fixed 1 CRITICAL in user-service
- Fixed by updating base image to `python:3.12.10-slim`

---

## 📊 Monitoring

| Dashboard | What It Shows |
|---|---|
| Kubernetes / Compute Resources / Cluster | Cluster CPU 5%, Memory 35% |
| Kubernetes / Compute Resources / Pod | Per-pod CPU, throttling, quota |
| Node Exporter / Nodes | EC2 CPU, Memory 48.7%, Disk, Network |
| Prometheus / Overview | Scrape targets, retrieval stats |

```bash
# Access Grafana
kubectl port-forward svc/monitoring-grafana -n monitoring 3000:80
# Open: http://localhost:3000
# Login: admin / DevSecOps@2026
```

---

## 🤖 Python AI Scripts

```bash
python3 ai-scripts/run_all.py
```

| Option | Script | Schedule |
|---|---|---|
| 1 | Auto Healer — detect + restart crashed pods | Every 30s |
| 2 | Log Analyzer — scan logs for anomalies | Every 1h |
| 3 | Cost Monitor — AWS cost + budget alerts | Every 24h |
| 4 | Security Scanner — Trivy ECR scan | Every 12h |
| 6 | Schedule All — run as daemon | Automatic |

---

## 💰 Cost Estimate

| Resource | Per Day | Per Month |
|---|---|---|
| EKS Control Plane | $2.40 | $72.00 |
| 2x t3.medium nodes | $2.30 | $69.12 |
| NAT Gateway | $1.08 | $32.40 |
| Load Balancers | $0.58 | $17.28 |
| EBS + ECR + S3 | $0.21 | $6.40 |
| **TOTAL** | **~$6.57** | **~$197** |

> 💡 Run `terraform destroy` when not using. Rebuild with `terraform apply` in 25-35 minutes.

---

## 🧹 Cleanup

```bash
cd terraform
terraform destroy
```

Deletes: EKS cluster, VPC, NAT Gateway, Load Balancers, EBS volumes, IAM roles
Keeps: ECR repos, S3 state bucket, GitHub repo

---

## 🐛 Common Issues

| Issue | Fix |
|---|---|
| EKS nodes not joining cluster | Add `aws_route_table_association` in vpc module |
| Pods CrashLoopBackOff | Check env vars: `kubectl describe deployment` |
| LoadBalancer showing internal | Add annotation `aws-load-balancer-scheme: internet-facing` |
| EBS PVC stuck Pending | Install EBS CSI driver addon on EKS |
| GitHub Actions OIDC failed | Verify GitHub username matches IAM trust policy |
| ECR image pull failed | Check node IAM role has ECR read policy |

---

## 📚 Key Learnings

- Terraform modular IaC design for production AWS
- OIDC keyless authentication eliminates credential sprawl
- GitOps with ArgoCD enforces declarative state management
- NAT Gateway required for private subnet internet access
- Helm templating enables reusable multi-service deployments
- Trivy scanning catches CVEs before they reach production
- Real debugging experience: 16 production-level issues resolved

---

## 👤 Author

**Rasika Deshmukh**
GitHub: [@rasika-08061998](https://github.com/rasika-08061998)

---

## 📄 License

Built for learning and portfolio purposes.
All code written from scratch as part of a DevSecOps learning journey.
