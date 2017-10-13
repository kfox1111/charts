# Minikube + OIDC Dashboard

This document describes how to launch a test Kubernetes system that has the dashboard secured by
OIDC via DEX.

# Install dependencies
You should download minikube, kubectl, and the helm client as recommended for your platform.

# Step 1
Create a minikube vm, create config files for dex and kubernetes-dashboard and disable the minikube provided dashboard.

Ctrl-C the watch once tiller is no longer unresponsive.

```console
which docker-machine-driver-kvm >/dev/null 2>&1 && EXTRARGS=--vm-driver=kvm
minikube start $EXTRARGS
COOKIESECRET=$(openssl rand -base64 32 | cut -c -32)
CLIENTPW=$(openssl rand -hex 11)
MINIKUBEIP=$(minikube ip)

cat > dex-minikube-values.yaml <<EOF
externalIPs:
- $MINIKUBEIP
inMiniKube: true
selfSigned:
  altIPs:
  - $MINIKUBEIP
config:
  issuer: "https://$MINIKUBEIP:5556"
  oauth2:
    skipApprovalScreen: true
  staticClients:
  - id: kubernetes
    redirectURIs:
    - 'http://$MINIKUBEIP:9090/oauth2/callback'
    name: 'Kubernetes Cluster'
    secret: $CLIENTPW
EOF
cat >> dex-minikube-values.yaml <<"EOF"
  enablePasswordDB: true
  staticPasswords:
  - email: "admin@example.com"
    # bcrypt hash of the string "password"
    hash: "$2a$10$2b2cU8CPhOTaGrs1HRQuAueS7JTT5ZHsHSzYiFPm1leZck7Mc8T4W"
    username: "admin"
    userID: "08a8684b-db88-4b73-90a9-3cd1661f5466"
EOF

cat > kubernetes-dashboard-minikube-values.yaml <<EOF
inMiniKube: true
externalIPs:
  - $MINIKUBEIP
httpPort: 9090
serviceType: NodePort
oidc:
  enabled: true
  selfSignedCA:
    configmap: dex-dex-ca
    key: dex-ca.pem
  args:
    - -http-address
    - 0.0.0.0:9090
    - -client-id 
    - kubernetes
    - -client-secret
    - "$CLIENTPW"
    - -pass-access-token
    - -redirect-url
    - http://$MINIKUBEIP:9090/oauth2/callback
    - -cookie-secret
    - "$COOKIESECRET"
    - -upstream
    - http://127.0.0.1:5557
    - -email-domain
    - "*"
    - -provider
    - oidc
    - -oidc-issuer-url
    - https://$MINIKUBEIP:5556
    - -ssl-insecure-skip-verify
    - -skip-provider-button
    - -cookie-secure=false
EOF

kubectl -n kube-system create sa tiller
kubectl create clusterrolebinding tiller --clusterrole cluster-admin --serviceaccount=kube-system:tiller
kubectl -n kube-system create sa kube-dns

helm init --service-account tiller
minikube addons disable dashboard

#wait for tiller not ready message to go away.
watch helm ls
```

# Step 2
Install DEX and wait for it to become available. This may take a 4-5 minutes.

Ctrl-C when all pods Ready.

```console
helm install --namespace kube-system -n dex stable/dex --values dex-minikube-values.yaml
kubectl patch deployment -n kube-system kube-dns -p '{"spec":{"template":{"spec":{"serviceAccount":"kube-dns"}}}}'

#wait for everything to enter Running state. It may take a few minutes.
watch kubectl get pods --all-namespaces
```

# Step 3
Shut down the vm, and enable RBAC and point the kube-apiserver at the DEX instance.

Ctrl-C when tiller not ready messages go away.
```console
minikube stop
minikube start --extra-config=apiserver.Authentication.OIDC.IssuerURL=https://$(minikube ip):5556 --extra-config=apiserver.Authentication.OIDC.ClientID=kubernetes --extra-config=apiserver.Authentication.OIDC.CAFile=/var/lib/localkube/oidc.pem --extra-config=apiserver.Authentication.OIDC.UsernameClaim=email --extra-config=apiserver.Authentication.OIDC.GroupsClaim=groups --extra-config=apiserver.Authorization.Mode=RBAC

#wait for tiller not ready message to go away.
watch helm ls
```

# Step 4
Install the Kubernetes Dashboard and the supporting Heapster service.
```console
helm install --namespace kube-system -n heapster stable/heapster --set rbac.create=true
helm install --namespace kube-system -n kubernetes-dashboard stable/kubernetes-dashboard/ --values kubernetes-dashboard-minikube-values.yaml
watch kubectl get pods --all-namespaces
```

# Access the dashboard
The default username configured above is: admin@example.com, and the password is: password
```console
minikube dashboard
```

# Give admin permission to a user
```console
kubectl create clusterrolebinding admin@example.com --clusterrole cluster-admin --user admin@example.com
```
