# Flannel CNI plugin

## QuickStart

```bash
$ helm install stable/flannel --name flannel --namespace kube-system
```

## Introduction

This chart bootstraps the Flannel SDN self hosted in Kubernetes.

## Prerequisites

- Kubernetes 1.6+
- Helm 2.3.1+ with helm init --net-host (Until released, Can use this helm: https://raw.githubusercontent.com/jascott1/bins/master/helm/nethost/_dist/linux-amd64/helm)
