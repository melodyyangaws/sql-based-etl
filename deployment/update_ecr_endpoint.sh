#!/bin/bash

    export ECR_IMAGE_URI=$(aws cloudformation describe-stacks --stack-name SparkOnEKS \
	--query "Stacks[0].Outputs[?OutputKey=='IMAGEURI'].OutputValue" \
	--output text)

	echo "Update ECR url in sample job files"
	sed -i.bak "s|{{ECR_URL}}|${ECR_IMAGE_URI}|g" source/example/*.yaml

	find . -type f -name "*.bak" -delete

