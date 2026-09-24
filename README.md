# GridOps

GridOps is a personal Kubernetes and cloud-native engineering project built as a hands-on environment for experimenting with modern infrastructure, GitOps, CI/CD, networking, security, and observability practices.

The application itself is intentionally simple: it provides a small web interface displaying Formula 1 racing information. The Formula 1 theme was chosen simply because I am a motorsport fan and makes the application more enjoyable to build while keeping the main focus of the project on the underlying platform and infrastructure.

> **Work in progress**
>
> GridOps is continuously evolving. Components, architecture, workflows, and configurations may change as new technologies and patterns are explored, implemented, tested, and improved.

## Goals

The main goal of GridOps is to provide a realistic environment where I can experiment with the lifecycle of a cloud-native application, from source code to deployment and observability.

The project is used to explore topics such as:

* Kubernetes architecture and workload management
* GitOps and declarative infrastructure
* CI/CD pipelines
* Container image lifecycle and automation
* Kubernetes networking and network policies
* Gateway API and traffic management
* TLS and certificate management
* Secrets management
* Metrics, tracing, and observability
* Infrastructure and application security
* Platform automation and operational practices

## Architecture

GridOps currently runs on a Kubernetes environment and follows a GitOps-based deployment model.

The main components include:

* **Kubernetes** — container orchestration platform
* **Cilium** — CNI, eBPF networking and network policies
* **Gateway API** — Kubernetes-native traffic routing
* **Envoy Gateway** — Gateway API implementation and ingress traffic management
* **cert-manager** — certificate lifecycle and TLS management
* **Flux CD** — GitOps reconciliation and deployment automation
* **Flux Image Automation** — automated container image discovery and manifest updates
* **GitHub Actions** — CI pipelines, validation and container image builds
* **GHCR** — private container image registry
* **OpenTelemetry** — application telemetry instrumentation and collection
* **Prometheus** — metrics collection and storage
* **Grafana** — metrics visualization and observability
* **SOPS** — encrypted secrets stored safely in Git

The application backend is built with **FastAPI** and consumes public motorsport data APIs to provide race-related information.

## Repository Structure

```text
.
├── app/
│   ├── backend/        # Application source code
│   ├── core/           # Kubernetes application resources
│   ├── monitoring/     # Application observability resources
│   └── route/          # Gateway API routing
│
├── flux/
│   ├── app/
│   ├── cert-manager/
│   ├── flux-system/
│   ├── image-automation/
│   ├── infra-gateways/
│   ├── infrastructure/
│   ├── monitoring/
│   └── namespaces/
│
└── infra/
    ├── cert-manager/
    ├── cilium/
    ├── envoy-gw/
    ├── gateway-api/
    ├── metrics-server/
    └── monitoring/
```

The repository is organized around a separation between the application, GitOps configuration, and underlying platform infrastructure.

## GitOps & CI/CD

GridOps follows a GitOps workflow where the desired state of the Kubernetes environment is stored in Git.

Changes committed to the repository are reconciled by Flux, while GitHub Actions handles CI tasks such as application validation, container image builds, security checks, and publishing images to GHCR.

Flux Image Automation monitors available application images and can automatically update the Kubernetes manifests when new eligible versions are published.

This creates an automated workflow broadly following:

```text
Code
  ↓
GitHub
  ↓
GitHub Actions
  ↓
Container Image
  ↓
GHCR
  ↓
Flux Image Automation
  ↓
Git Repository
  ↓
Flux Reconciliation
  ↓
Kubernetes
```

## Observability

The project is progressively adopting OpenTelemetry as the standard telemetry layer.

The application exports telemetry using OTLP to an OpenTelemetry Collector running inside the cluster. The collector processes and exposes telemetry to the observability stack, including Prometheus and Grafana.

This area of the project is also actively evolving and is used to experiment with metrics, traces, dashboards, alerting, and Kubernetes-level observability.

## Security

GridOps is also used to experiment with security practices across the application and platform, including:

* Kubernetes NetworkPolicies
* CiliumNetworkPolicy
* namespace isolation
* TLS termination
* certificate management
* encrypted GitOps secrets with SOPS
* private container registries
* CI security and secret scanning
* workload and infrastructure hardening

Security controls are progressively introduced as part of the project's development rather than treated as a finished production security model.

## Project Status

GridOps is a **learning and experimentation project**, not a production service.

There is intentionally no fixed final architecture.

The platform is continuously modified as I explore new Kubernetes and cloud-native technologies, replace components, test different architectural approaches, and improve existing implementations.

Expect things to change.

## Formula 1 Disclaimer

The Formula 1 theme is used solely as the subject of this personal, non-commercial learning project.

This project is unofficial and is not endorsed by, affiliated with, or associated with Formula 1, the FIA, any Formula 1 team, driver, sponsor, or related organization.

Formula 1 publishes specific guidelines governing fan and editorial use of its intellectual property and trademarks.

**This website is unofficial and is not associated in any way with the Formula 1 companies. F1, FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD CHAMPIONSHIP, GRAND PRIX and related marks are trade marks of Formula One Licensing B.V.**

All trademarks, team names, driver names, logos, and other intellectual property referenced by the project remain the property of their respective owners.

No ownership of Formula 1-related intellectual property is claimed by this project.

## Data Sources

Race information displayed by GridOps may be obtained from third-party or publicly available APIs.

Those services and their data remain subject to their respective terms, licenses, availability, and usage policies.

GridOps does not claim ownership of third-party data.

## License

The source code and original configuration contained in this repository may be distributed under the license specified in the repository's `LICENSE` file.

Third-party trademarks, data, logos, names, and other intellectual property referenced by the project are **not** covered by that license and remain the property of their respective owners.
