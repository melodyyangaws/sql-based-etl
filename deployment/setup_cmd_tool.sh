#!/bin/bash

# install k8s command tool kubectl 
curl -o kubectl "https://amazon-eks.s3.us-west-2.amazonaws.com/1.18.9/2020-11-02/bin/linux/amd64/kubectl"
chmod +x kubectl
mkdir -p $HOME/bin && mv kubectl $HOME/bin/kubectl && export PATH=$PATH:$HOME/bin
kubectl version

# install Argo CLI tool
VERSION=$(curl --silent "https://api.github.com/repos/argoproj/argo/releases/latest" | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
curl -sLO https://github.com/argoproj/argo/releases/download/${VERSION}/argo-darwin-amd64.gz
gunzip argo-darwin-amd64.gz
chmod +x argo-darwin-amd64
mv ./argo-darwin-amd64 /usr/local/bin/argo
argo version --short