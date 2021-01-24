#!/bin/bash


if [ $# -eq 0 ]; then
    echo "No argument is supplied."
	echo "USAGE: pull_and_push_ecr.sh <region> <acct_name> <repo_name> <optional:skip_ecr_step>"
	echo "EXAMPLE1: pull_and_push_ecr.sh 'us-west-2' 123456789 'arc' "
	echo "EXAMPLE2: pull_and_push_ecr.sh 'us-west-2' 123456789 'arc' 'skip_ecr' "

else

    export CDK_DEPLOY_REGION=${1}
    export CDK_DEPLOY_ACCOUNT=${2}

	if [[ $4 == '' ]]; then
		echo "Creating repositories and push docker images to ECR"
		REPO_NAME=${3}

		echo "Creating ECR repositories"
		aws ecr describe-repositories --repository-names $REPO_NAME --region $CDK_DEPLOY_REGION || aws ecr --region $CDK_DEPLOY_REGION create-repository --repository-name $REPO_NAME --image-scanning-configuration scanOnPush=true

		echo "Logging into ECR"
		aws ecr get-login-password --region $CDK_DEPLOY_REGION | docker login --username AWS --password-stdin $CDK_DEPLOY_ACCOUNT.dkr.ecr.$CDK_DEPLOY_REGION.amazonaws.com

		echo "Build image ${REPO_NAME}"
		docker build -t $CDK_DEPLOY_ACCOUNT.dkr.ecr.$CDK_DEPLOY_REGION.amazonaws.com/$REPO_NAME .

		echo "Push image ${REPO_NAME}"
		docker push $CDK_DEPLOY_ACCOUNT.dkr.ecr.$CDK_DEPLOY_REGION.amazonaws.com/$REPO_NAME:latest
		echo "The image $REPO_NAME is pushed to ECR"
		
	fi	

	# echo "Set up deployment file"
	# sed -i.bak "s/{{ACCOUNTNUMBER}}/$CDK_DEPLOY_ACCOUNT/" deployment/environment.cfg
	# sed -i.bak "s/{{REGION}}/$CDK_DEPLOY_REGION/" deployment/environment.cfg

	echo "Update ECR url in sample job files"
	sed -i.bak "s/{{ACCOUNTNUMBER}}/$CDK_DEPLOY_ACCOUNT/" source/example/*.yaml
	sed -i.bak "s/{{REGION}}/$CDK_DEPLOY_REGION/" source/example/*.yaml

	find . -type f -name "*.bak" -delete
fi
