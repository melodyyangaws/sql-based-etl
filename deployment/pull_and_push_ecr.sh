#!/bin/bash


if [ $# -eq 0 ]; then
    echo "No argument is supplied."
	echo "USAGE: pull_and_push_ecr.sh <region> <repo_name> <optional:skip_ecr_step>"
	echo "EXAMPLE1: pull_and_push_ecr.sh <region> 'arc' "
	echo "EXAMPLE2: pull_and_push_ecr.sh <region> 'arc' 'skip' "

else

    export AWS_REGION=${1}
    export CDK_DEPLOY_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

	if [[ $3 == '' ]]; then
		echo "Creating repositories and push docker images to ECR"
		REPO_NAME=${2}

		echo "Creating ECR repositories"
		aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION || aws ecr --region $AWS_REGION create-repository --repository-name $REPO_NAME --image-scanning-configuration scanOnPush=true

		echo "Logging into ECR"
		aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $CDK_DEPLOY_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com

		echo "Build image ${REPO_NAME}"
		docker build -t $CDK_DEPLOY_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME .

		echo "Push image ${REPO_NAME}"
		docker push $CDK_DEPLOY_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest
		echo "The image $REPO_NAME is pushed to ECR"
		
	fi	

	# echo "Set up deployment file"
	# sed -i.bak "s/{{ACCOUNTNUMBER}}/$CDK_DEPLOY_ACCOUNT/" deployment/environment.cfg
	# sed -i.bak "s/{{REGION}}/$AWS_REGION/" deployment/environment.cfg

	echo "Update ECR url in sample job files"
	sed -i.bak "s/{{ACCOUNTNUMBER}}/$CDK_DEPLOY_ACCOUNT/" source/example/*.yaml
	sed -i.bak "s/{{REGION}}/$AWS_REGION/" source/example/*.yaml
	find . -type f -name "*.bak" -delete

fi
