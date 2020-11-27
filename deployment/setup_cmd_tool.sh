#!/bin/bash

# install k8s command tool kubectl 
curl -o kubectl "https://amazon-eks.s3.us-west-2.amazonaws.com/1.18.9/2020-11-02/bin/linux/amd64/kubectl"
chmod +x kubectl
mkdir -p $HOME/bin && mv kubectl $HOME/bin/kubectl && export PATH=$PATH:$HOME/bin
# install argo workflow management tool
export ARGO_VERSION="v2.11.8"
curl -sLO https://github.com/argoproj/argo/releases/download/${ARGO_VERSION}/argo-linux-amd64
chmod +x argo-linux-amd64
mv argo-linux-amd64 /usr/local/bin/argo