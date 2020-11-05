#!/bin/bash


if [ $# -eq 0 ]; then
    echo "No argument is supplied. Skip the ECR step."
	echo "USAGE: pull_and_push_ecr.sh <region> <acct_name> <repo_name> <optional:build the image or not>"
	echo "EXAMPLE1: pull_and_push_ecr.sh 'us-west-2' 123456789 'arc' 1 "
	echo "EXAMPLE2: pull_and_push_ecr.sh 'us-west-2' 123456789 'arc-jupyter'"
else

	export REGION=${1}
	export ACCOUNTNUMBER=${2}

	echo "Creating repositories and push docker images to ECR"
	REPO_NAME=${3}

	echo "Creating ECR repositories"
	aws ecr describe-repositories --repository-names $REPO_NAME --region $REGION || aws ecr --region $REGION create-repository --repository-name $REPO_NAME --image-scanning-configuration scanOnPush=true
	

	echo "Logging into ECR"
	aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNTNUMBER.dkr.ecr.$REGION.amazonaws.com

	if [[ $4 != '' ]]; then
		echo "Build image ${REPO_NAME}"
		docker build -t $ACCOUNTNUMBER.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME .
	else
		echo "Pull image ${REPO_NAME}"
		docker pull ghcr.io/tripl-ai/$REPO_NAME:latest
		docker tag ghcr.io/tripl-ai/$REPO_NAME:latest $ACCOUNTNUMBER.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest
	fi

	echo "Push image ${REPO_NAME}"
	docker push $ACCOUNTNUMBER.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest
	echo "The image $REPO_NAME is pushed to ECR"
	
fi	

echo "Setting up deployment files"
sed -i.bak "s/{{ACCOUNTNUMBER}}/$ACCOUNTNUMBER/" deployment/environment.cfg
sed -i.bak "s/{{REGION}}/$REGION/" deployment/environment.cfg

echo "Replace account number in job configuration files"
sed -i.bak "s/{{ACCOUNTNUMBER}}/$ACCOUNTNUMBER/" source/app_resources/*-job.yaml

find . -type f -name "*.bak" -delete
