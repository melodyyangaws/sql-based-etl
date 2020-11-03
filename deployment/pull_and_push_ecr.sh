#!/bin/bash


if [ $# -eq 0 ]; then
    echo "No argument is supplied. Skip the ECR step."
	echo "USAGE1: pull_and_push_ecr.sh region=region AcctName=account repo_name=arc build=1"
	echo "USAGE2: pull_and_push_ecr.sh region=region AcctName=account repo_name=arc-jupyter"
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
sed -i.bak "s/\ACCOUNTNUMBER\b/$ACCOUNTNUMBER/" deployment/environment.cfg
sed -i.bak "s/\REGION\b/$REGION/" deployment/environment.cfg
find . -type f -name "*.bak" -delete