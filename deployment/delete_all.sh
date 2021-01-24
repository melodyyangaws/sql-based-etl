#!/bin/bash


echo "Delete a container repository from ECR"
aws ecr delete-repository --repository-name arc --force


echo "Drop a Delta Lake table default.contact_snapshot"
aws athena start-query-execution --query-string "DROP TABLE default.contact_snapshot" --result-configuration OutputLocation=s3://sparkoneks/


echo "Delete ALB"
# delete ALB
argoALB=$(aws elbv2 describe-load-balancers --query 'LoadBalancers[?starts_with(DNSName,`k8s-argo`)==`true`].LoadBalancerArn' --output text --region us-west-2)
jhubALB=$(aws elbv2 describe-load-balancers --query 'LoadBalancers[?starts_with(DNSName,`k8s-jupyter`)==`true`].LoadBalancerArn' --output text --region us-west-2)

aws elbv2 delete-load-balancer --load-balancer-arn $argoALB
aws elbv2 delete-load-balancer --load-balancer-arn $jhubALB
sleep 15

echo "Delete Target groups"
argoTG=$(aws elbv2 describe-target-groups --query 'TargetGroups[?starts_with(TargetGroupName,`k8s-argo`)==`true`].TargetGroupArn' --output text)
jhubTG=$(aws elbv2 describe-target-groups --query 'TargetGroups[?starts_with(TargetGroupName,`k8s-jupyter`)==`true`].TargetGroupArn' --output text)

aws elbv2 delete-target-group --target-group-arn $argoTG 
aws elbv2 delete-target-group --target-group-arn $jhubTG 


echo "Delete the rest of Cloud resources via CDK CLI"
cdk destroy


