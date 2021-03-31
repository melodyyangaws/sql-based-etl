# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: MIT-0

from aws_cdk import (
    core, 
    aws_eks as eks,
    aws_secretsmanager as secmger,
    aws_kms as kms
)
from bin.network_sg import NetworkSgConst
from bin.iam_roles import IamConst
from bin.eks_cluster import EksConst
from bin.eks_service_account import EksSAConst
from bin.eks_base_app import EksBaseAppConst
from bin.s3_app_code import S3AppCodeConst
from bin.spark_permission import SparkOnEksSAConst
from lib.cloud_front_stack import NestedStack
from bin.manifest_reader import *
import bin.override_rule as scan
import json

class SparkOnEksStack(core.Stack):

    @property
    def code_bucket(self):
        return self.app_s3.code_bucket

    @property
    def argo_url(self):
        return self._argo_alb.value

    @property
    def jhub_url(self):
        return self._jhub_alb.value

    def __init__(self, scope: core.Construct, id: str, eksname: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.template_options.description = "(SO0141) SQL based ETL with Apache Spark on Amazon EKS. This solution provides a SQL based ETL option with a open-source declarative framework powered by Apache Spark."

        # Cloudformation input params
        datalake_bucket = core.CfnParameter(self, "datalakebucket", type="String",
            description="Your existing S3 bucket to be accessed by Jupyter Notebook and ETL job. Default: blank",
            default=""
        )
        login_name = core.CfnParameter(self, "jhubuser", type="String",
            description="Your username login to jupyter hub",
            default="sparkoneks"
        )

        # Auto-generate a user login in secrets manager
        key = kms.Key(self, 'secretsKMSKey',removal_policy=core.RemovalPolicy.DESTROY,enable_key_rotation=True)
        key.add_alias('alias/secresmgr')
        jhub_secret = secmger.Secret(self, 'jHubPwd', 
            generate_secret_string=secmger.SecretStringGenerator(
                exclude_punctuation=True,
                secret_string_template=json.dumps({'username': login_name.value_as_string}),
                generate_string_key="password"),
            removal_policy=core.RemovalPolicy.DESTROY,
            encryption_key=key
        )

        # A new bucket to store app code and access logs
        self.app_s3 = S3AppCodeConst(self,'appcode')

        # 1. Setup EKS base infrastructure
        network_sg = NetworkSgConst(self,'network-sg', eksname, self.app_s3.code_bucket)
        iam = IamConst(self,'iam_roles', eksname)
        eks_cluster = EksConst(self,'eks_cluster', eksname, network_sg.vpc, iam.managed_node_role, iam.admin_role)
        eks_security = EksSAConst(self, 'eks_sa', eks_cluster.my_cluster, jhub_secret)
        eks_base_app = EksBaseAppConst(self, 'eks_base_app', eks_cluster.my_cluster, core.Aws.REGION)

        # 2. Setup Spark application access control
        app_security = SparkOnEksSAConst(self,'spark_service_account', 
            eks_cluster.my_cluster, 
            login_name.value_as_string,
            self.app_s3.code_bucket,
            datalake_bucket.value_as_string
        )
        
        # 3. Install ETL orchestrator - Argo
        # can be replaced by other workflow tool, ie. Airflow
        argo_install = eks_cluster.my_cluster.add_helm_chart('ARGOChart',
            chart='argo',
            repository='https://argoproj.github.io/argo-helm',
            release='argo',
            namespace='argo',
            create_namespace=True,
            values=loadYamlLocal('../app_resources/argo-values.yaml')
        )
        # Create a Spark workflow template with different T-shirt size
        submit_tmpl = eks_cluster.my_cluster.add_manifest('SubmitSparkWrktmpl',
            loadYamlLocal('../app_resources/spark-template.yaml')
        )
        submit_tmpl.node.add_dependency(argo_install)

        # 4. Install Arc Jupyter notebook to as Spark ETL IDE
        jhub_install= eks_cluster.my_cluster.add_helm_chart('JHubChart',
            chart='jupyterhub',
            repository='https://jupyterhub.github.io/helm-chart',
            release='jhub',
            version='0.11.1',
            namespace='jupyter',
            create_namespace=False,
            values=loadYamlReplaceVarLocal('../app_resources/jupyter-values.yaml', 
                fields={
                    "{{codeBucket}}": self.app_s3.code_bucket,
                    "{{region}}": self.region 
                })
        )

        # get Arc Jupyter login from secrets manager
        name_parts= core.Fn.split('-',jhub_secret.secret_name)
        name_no_suffix=core.Fn.join('-',[core.Fn.select(0, name_parts), core.Fn.select(1, name_parts)])

        config_hub = eks.KubernetesManifest(self,'JHubConfig',
            cluster=eks_cluster.my_cluster,
            manifest=loadYamlReplaceVarLocal('../app_resources/jupyter-config.yaml', 
                fields= {
                    "{{MY_SA}}": app_security.jupyter_sa,
                    "{{REGION}}": self.region, 
                    "{{SECRET_NAME}}": name_no_suffix
                }, 
                multi_resource=True)
        )
        config_hub.node.add_dependency(jhub_install)
   
        # 5.(OPTIONAL) retrieve ALB DNS Name to enable Cloudfront in the following nested stack.
        # Recommend to remove this section and the rest of CloudFront component. 
        # Setup your own certificate then add to ALB, to enable the HTTPS.
        self._argo_alb = eks.KubernetesObjectValue(self, 'argoALB',
            cluster=eks_cluster.my_cluster,
            json_path='.status.loadBalancer.ingress[0].hostname',
            object_type='ingress',
            object_name='argo-server',
            object_namespace='argo'
        )
        self._argo_alb.node.add_dependency(argo_install)

        self._jhub_alb=eks.KubernetesObjectValue(self, 'jhubALB',
            cluster=eks_cluster.my_cluster,
            json_path='.status.loadBalancer.ingress[0].hostname',
            object_type='ingress',
            object_name='jupyterhub',
            object_namespace='jupyter'
        )
        self._jhub_alb.node.add_dependency(config_hub)

# //************************************v*************************************************************//
# //********************* Override cfn Nag scan rules for CICD deployment ***************************//
# //***********************************************************************************************//   
        scan.suppress_cfnNag_rule('W12', 'by default the role has * resource', self.node.find_child('eks_cluster').node.find_child('EKS').node.find_child('Resource').node.find_child('CreationRole').node.find_child('DefaultPolicy').node.default_child)
        scan.suppress_cfnNag_rule('W11', 'by default the role has * resource', self.node.find_child('Custom::AWSCDKOpenIdConnectProviderCustomResourceProvider').node.find_child('Role'))
        scan.suppress_cfnNag_rule('W58','the service role has permission to write logs to CloudWatch',self.node.find_child('Custom::S3AutoDeleteObjectsCustomResourceProvider').node.find_child('Handler'))
        scan.suppress_cfnNag_rule('W58','the service role has permission to write logs to CloudWatch',self.node.find_child('Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C').node.find_child('Resource'))
        scan.suppress_cfnNag_rule('W58','the service role has permission to write logs to CloudWatch',self.node.find_child('Custom::AWSCDKOpenIdConnectProviderCustomResourceProvider').node.find_child('Handler'))
        scan.suppress_cfnNag_rule('W58','the service role has permission to write logs to CloudWatch',self.node.find_child('AWSCDKCfnUtilsProviderCustomResourceProvider').node.find_child('Handler'))
        scan.suppress_cfnNag_rule('W58','the service role has permission to write logs to CloudWatch',self.node.find_child('@aws-cdk--aws-eks.KubectlProvider').node.find_child('Handler').node.default_child)
        scan.suppress_cfnNag_rule('W58','the service role has permission to write logs to CloudWatch',self.node.find_child('@aws-cdk--aws-eks.KubectlProvider').node.find_child('Provider').node.find_child('framework-onEvent').node.default_child)
        scan.suppress_cfnNag_rule('W58','the service role has permission to write logs to CloudWatch',self.node.find_child('@aws-cdk--aws-eks.ClusterResourceProvider').node.find_child('OnEventHandler').node.find_child('Resource'))
        scan.suppress_cfnNag_rule('W58','the service role has permission to write logs to CloudWatch',self.node.find_child('@aws-cdk--aws-eks.ClusterResourceProvider').node.find_child('IsCompleteHandler').node.find_child('Resource'))
        scan.suppress_cfnNag_rule('W58','the service role has permission to write logs to CloudWatch',self.node.find_child('@aws-cdk--aws-eks.ClusterResourceProvider').node.find_child('Provider').node.find_child('framework-isComplete').node.find_child('Resource'))
        scan.suppress_cfnNag_rule('W58','the service role has permission to write logs to CloudWatch',self.node.find_child('@aws-cdk--aws-eks.ClusterResourceProvider').node.find_child('Provider').node.find_child('framework-onTimeout').node.find_child('Resource'))
        scan.suppress_cfnNag_rule('W58','the service role has permission to write logs to CloudWatch',self.node.find_child('@aws-cdk--aws-eks.ClusterResourceProvider').node.find_child('Provider').node.find_child('framework-onEvent').node.find_child('Resource'))
        self.node.find_child('eks_cluster').node.find_child('EKS').node.find_child('ControlPlaneSecurityGroup').node.default_child.add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W40",
                    "reason": "Egress IP Protocol of -1 is default and generally considered OK"
                },
                {
                    "id": "W5",
                    "reason": "Security Groups with cidr open considered OK"
                }
            ]
        })

       
