from aws_cdk import (
    core,
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_iam as iam
)
# from lib.worker_iam import IamConst
from lib.eks_control_plane import EksConst
from lib.manifest_reader import loadManifestYamlLocal

class WorkerNodeConst(core.Construct):
    def __init__(self,scope: core.Construct, id: str, eks_cluster: EksConst,**kwargs,) -> None:
        super().__init__(scope, id, **kwargs)

        _my_cluster=eks_cluster.cluster
        # _iam_construct = IamConst(self,'create-worker-iam',_my_cluster.cluster_name)


# //*********************************************************************//
# //******************** Add Managed Worker Node to EKS ******************//
# //*********************************************************************//
        # add managed node group 
        _my_cluster.add_nodegroup_capacity('managed-nodegroup',
            nodegroup_name='etl-job',
            desired_size=1,
            max_size=2,
            min_size=1,
            disk_size=50,
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.MEMORY5,ec2.InstanceSize.XLARGE),
            labels={'app':'spark'},
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE,one_per_az=True),
        )
        

# //************* SETUP ETL JOBS IN ARGO *************//
        argo_chart=_my_cluster.add_helm_chart('argo-chart',
            chart='argo',
            repository='https://argoproj.github.io/argo-helm',
            release='argo',
            namespace='argo',
            create_namespace=True
        )

        # Create k8s Service account and corresponding IAM Role mapped via IRSA
        etl_service_account = _my_cluster.add_service_account(
            "etl-service",
            name="etl",
            namespace="argo"
        )

        etl_service_account.node.add_dependency(argo_chart)
        etl_service_account.add_to_policy(iam.PolicyStatement(
                resources=['*'],
                actions=["secretsmanager:GetSecretValue", 
                        "s3:ListBucket", "s3:PutObject","s3:GetObject","s3:DeleteObject"]
            )
        )
        argo_rbac=_my_cluster.add_manifest('role-binding',
            (loadManifestYamlLocal('../app_resources/argo-workflow-rbac.yaml'))
        )


        # TO DO
        # create argo workflow template:kubectl apply -f app_resources/arc-workflow-template.yaml -n argo
        # submit spark ETL job to ARGO: kubectl apply -f app_resources/nyctaxi.yaml -n argo --serviceaccount etl 
        ##########

        # _my_cluster.add_manifest('arc-job-template',
        #     (loadManifestYamlLocal('../app_resources/arc-workflow-template.yaml'))
        # )
        # _my_cluster.add_manifest('submit-arc-job',
        #     (loadManifestYamlLocal('../app_resources/nyctaxi.yaml'))
        # )
        
# //***************** Submit Native Spark job ******************//
# TO DO
    # submit native spark job to k8s: kubectl apply -f app_resources/kinnar.yaml -n spark --sercviceaccount etl
 ##########


# //*********************************************************************//
# //********************* Add Farget to EKS **********************//
# //*********************************************************************//
        # # add fargate node
        # _my_cluster.add_fargate_profile('fargate-nodes',
        #     selectors=[{"labels": {"app": "spark"},
        #                 "namespace": "jupyter"}
        #     ],
        #     fargate_profile_name='jupyterhub',
        #     # pod_execution_role=_iam_construct.fargate_role,
        #     subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE, one_per_az=True),
        
        # )

        # _my_cluster.add_helm_chart('jupyter-chart',
        #     chart='jupyterhub',
        #     repository='https://jupyterhub.github.io/helm-chart',
        #     # release='jupyter',
        #     namespace='jupyter',
        #     values=['overwrite',loadManifestYamlLocal('../app_resources/jupyterconfig.yaml')]
        # )

        # _my_cluster.add_service_account('jupyterhub',name='notebook',namespace='jupyter')