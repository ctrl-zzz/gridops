# TODO Kubernetes Platform

Checklist ordinata per priorita. Le attivita di una stessa sezione sono elencate indicativamente nell'ordine in cui affrontarle.

## P0 - Ripristinare un bootstrap GitOps affidabile

- [ ] Dichiarare e riconciliare il namespace `cert-manager` prima del relativo `HelmRelease`.
- [ ] Correggere il namespace del `HelmRepository` referenziato dal `HelmRelease` del monitoring.
- [ ] Uniformare i namespace di Envoy Gateway tra manifest Flux, policy di rete e script di bootstrap.
- [ ] Verificare namespace e label dei proxy generati da Envoy Gateway.
- [ ] Verificare le Cilium network policy rispetto alla porta effettiva del backend (`8000`) usando anche `cilium policy trace`.
- [ ] Rendere le Flux `Kustomization` piu granulari, separando almeno namespace, CRD, controller, configurazioni infrastrutturali e applicazioni, cosi che il guasto di un componente non blocchi l'intera riconciliazione.
- [ ] Ordinare le Flux `Kustomization` con `dependsOn`, `wait`, health check e timeout espliciti.
- [ ] Configurare retry, remediation e rollback appropriati per installazione e aggiornamento dei `HelmRelease`.
- [ ] Provare e documentare il bootstrap completo partendo da un cluster Kind vuoto, senza preinstallazioni manuali.
- [ ] Eliminare o archiviare gli installer imperativi che competono con le risorse gestite da Flux.

## P1 - Sicurezza e affidabilita di base

- [ ] Eseguire l'applicazione con UID e GID non root fissi.
- [ ] Applicare un `securityContext` restricted con `runAsNonRoot`, `allowPrivilegeEscalation: false`, capabilities rimosse, seccomp `RuntimeDefault` e root filesystem read-only.
- [ ] Usare un ServiceAccount dedicato e disabilitare `automountServiceAccountToken` dove l'accesso alle API Kubernetes non serve.
- [ ] Aggiungere startup, readiness e liveness probe.
- [ ] Definire CPU e memoria `requests` e `limits` sulla base di misurazioni.
- [ ] Aggiungere `LimitRange` e `ResourceQuota` ai namespace applicativi.
- [ ] Applicare gradualmente Pod Security Admission con profilo `restricted`.
- [ ] Aggiungere un `PodDisruptionBudget`.
- [ ] Distribuire le repliche tra nodi e zone mediante topology spread constraints o pod anti-affinity.
- [ ] Definire esplicitamente la strategia di rolling update.
- [ ] Valutare un HPA dopo aver configurato risorse e raccolto metriche rappresentative.
- [ ] Rimuovere `--kubelet-insecure-tls` da metrics-server fuori dall'ambiente locale.
- [ ] Sostituire la password amministrativa predefinita di Grafana con un secret cifrato e ruotato.
- [ ] Sostituire il certificato direttamente self-signed con ACME o una PKI interna attendibile negli ambienti non locali.
- [ ] Limitare il piu possibile le credenziali statiche e automatizzarne provisioning e rotazione, inclusi i token GitHub oggi creati manualmente.

## P1 - Network policy

- [ ] Revisionare tutte le network policy esistenti e verificare con test automatici che non blocchino i flussi previsti.
- [ ] Definire policy default-deny esplicite per ingress ed egress in ogni namespace.
- [ ] Definire una policy DNS allow dedicata e riutilizzabile per ogni workload che ne abbia bisogno.
- [ ] Definire policy allow minime per ogni singolo componente applicativo e infrastrutturale.
- [ ] Limitare l'egress dell'applicazione alle sole destinazioni necessarie, valutando le Cilium FQDN policy.
- [ ] Evitare selettori dipendenti da label interne e instabili dei chart Helm.
- [ ] Aggiungere test end-to-end Gateway-to-backend e test negativi per i flussi vietati.
- [ ] Valutare `externalTrafficPolicy: Local` e verificare la conservazione dell'IP sorgente.

## P2 - Struttura, naming e metadati

- [ ] Ridisegnare e rinominare file e directory in modo coerente con ambienti, componenti e responsabilita.
- [ ] Rinominare i componenti usando nomi sintetici, appropriati e consistenti.
- [ ] Applicare label a tutte le risorse per proprieta, componente, ambiente e gestione.
- [ ] Uniformare le label alle Kubernetes recommended labels `app.kubernetes.io/*`.
- [ ] Rendere espliciti hostname, listener `sectionName` e path nelle `HTTPRoute`.
- [ ] Valutare un redirect HTTP permanente `308` al posto di `301`.
- [ ] Creare overlay Kustomize distinti per `lab`, `staging` e `production`.
- [ ] Isolare nell'overlay `lab` endpoint Kind, pool IP locale, dominio `.local`, TLS insicuro e configurazioni specifiche del laboratorio.

## P2 - Osservabilita e accesso ai servizi infra

- [ ] Rimuovere `prometheus-fastapi-instrumentator` in favore dell'instrumentation ufficiale OpenTelemetry.
- [ ] Esporre metriche e health endpoint su una porta dedicata, separata da quella del traffico applicativo.
- [ ] Aggiornare Service, ServiceMonitor e network policy per la porta metriche dedicata.
- [ ] Configurare persistenza o remote write per Prometheus.
- [ ] Configurare Alertmanager con receiver reali.
- [ ] Definire alert, dashboard, recording rule e SLO per applicazione e piattaforma.
- [ ] Aggiungere logging strutturato, tracing distribuito e metriche sulle dipendenze esterne.
- [ ] Aggiungere test sintetici del percorso Gateway-to-backend.
- [ ] Esporre Grafana tramite Gateway API senza ricorrere al port-forward.
- [ ] Proteggere Grafana e gli altri servizi infrastrutturali con SSO e autorizzazioni coerenti.

## P2 - CI, supply chain e dipendenze

- [ ] Aggiungere GitHub Actions per lint, render Kustomize, validazione schema, policy check, secret scanning, vulnerability scanning e controlli di sicurezza.
- [ ] Configurare la GitHub Action applicativa esistente affinche si attivi sulle modifiche ai file applicativi, non soltanto sui tag.
- [ ] Aggiungere test di connettivita e smoke test post-deploy.
- [ ] Adottare Semantic Versioning e Conventional Commits, automatizzando changelog e release dove opportuno.
- [ ] Configurare Renovate per immagini, chart Helm, manifest Kubernetes, GitHub Actions e dipendenze applicative; valutare uno strumento alternativo solo per gli ecosistemi non supportati adeguatamente.
- [ ] Bloccare immagini applicative e immagini base tramite digest.
- [ ] Bloccare la versione di `kube-prometheus-stack`.
- [ ] Bloccare tutte le dipendenze Python con lockfile e hash verificabili.
- [ ] Generare SBOM e scansioni di vulnerabilita per le immagini.
- [ ] Firmare immagini e artefatti e verificarli tramite admission policy.
- [ ] Vendorizzare o rendere immutabili e verificabili le dipendenze Kustomize remote.
- [ ] Proteggere i branch e promuovere commit o artefatti revisionati tra gli ambienti.

## P2 - Manutenzione repository e secret

- [ ] Sistemare `.gitignore` includendo almeno `.venv`, `__pycache__`, `*.pyc`, cache dei test e output di build, preferibilmente partendo dal template di Toptal gitignore generator.
- [ ] Rimuovere dal versionamento i file bytecode Python gia tracciati.
- [ ] Documentare creazione, backup, ripristino e rotazione della chiave SOPS age usata da Flux.
- [ ] Usare credenziali GHCR read-only, con scope minimo e rotazione automatizzata.
- [ ] Valutare External Secrets Operator quando verra introdotto Vault.

## P3 - Migliorie applicative e dati

- [ ] Aggiungere retry limitati con jitter, timeout differenziati, cache, circuit breaker e fallback per OpenF1.
- [ ] Riutilizzare il pool di connessioni HTTP e misurare latenza ed errori delle chiamate esterne.
- [ ] Mantenere la readiness indipendente da indisponibilita temporanee dei servizi di terze parti.
- [ ] Introdurre un database gestito in Kubernetes, valutando CloudNativePG, solo dopo aver definito requisiti di persistenza, backup, restore e alta disponibilita.
- [ ] Definire backup, point-in-time recovery, test periodici di restore e monitoraggio del database.

## P3 - Evoluzione della piattaforma

- [ ] Implementare una base cluster riproducibile con Talos Linux, Terraform e provider libvirt.
- [ ] Separare chiaramente provisioning dell'infrastruttura, bootstrap Flux e gestione dichiarativa dei workload.
- [ ] Valutare se Cilium Gateway API possa sostituire Envoy Gateway per i requisiti effettivi, confrontando feature, maturita, operativita e complessita.
- [ ] Studiare Crossplane e valutarne l'integrazione quando verranno introdotti Vault e risorse esterne gestite dichiarativamente.
- [ ] Studiare GitHub Actions Runner Controller (ARC), inclusi isolamento, autoscaling, credenziali, cache e rischio di eseguire workflow non fidati nel cluster.

## P4 - Evoluzioni di lungo periodo

- [ ] Valutare la sostituzione di OpenF1 con una sorgente dati che non richieda autenticazione o pagamento e che non diventi indisponibile durante il passaggio tra sessioni.
- [ ] Migrare soltanto dopo aver confrontato licenza, affidabilita, limiti, latenza, qualita dei dati e continuita del servizio.
