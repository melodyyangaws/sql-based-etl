#!/bin/bash

echo "Creating repositories and push docker images to ECR"


echo "Creating ECR repositories"
aws ecr --region $REGION create-repository --repository-name arc-jupyter  --image-scanning-configuration scanOnPush=true
aws ecr --region $REGION create-repository --repository-name arc  --image-scanning-configuration scanOnPush=true


echo "Logging into ECR"
$(aws --region $REGION ecr get-login --no-include-email)
if [[ $? -ne 0 ]];then
	aws ecr get-login-password --region REGION | docker login --username AWS --password-stdin $ACCOUNTNUMBER.dkr.ecr.$REGION.amazonaws.com
fi

echo "Pull and push image for arc-jupyter"
docker pull ghcr.io/tripl-ai/arc-jupyter:arc-jupyter_3.6.0_scala_2.12_hadoop_3.2.0_1.0.0
docker tag ghcr.io/tripl-ai/arc-jupyter:arc-jupyter_3.6.0_scala_2.12_hadoop_3.2.0_1.0.0 $ACCOUNTNUMBER.dkr.ecr.$REGION.amazonaws.com/arc-jupyter:latest
docker push $ACCOUNTNUMBER.dkr.ecr.$REGION.amazonaws.com/arc-jupyter:latest

echo "Pull and push image for arc"
docker pull ghcr.io/tripl-ai/arc:arc_3.4.0_spark_3.0.1_scala_2.12_hadoop_3.2.0_1.0.0
docker tag ghcr.io/tripl-ai/arc:arc_3.4.0_spark_3.0.1_scala_2.12_hadoop_3.2.0_1.0.0 $ACCOUNTNUMBER.dkr.ecr.$REGION.amazonaws.com/arc:latest
docker push $ACCOUNTNUMBER.dkr.ecr.$REGION.amazonaws.com/arc:latest

echo "Setting up deployment files with new image details"
sed -i.bak "s/ACCOUNTNUMBER/$ACCOUNTNUMBER/" ./environment.cfg
sed -i.bak "s/REGION/$REGION/" ./environment.cfg