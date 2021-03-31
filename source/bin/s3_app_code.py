from aws_cdk import (
    core, 
    aws_s3 as s3,
    aws_s3_deployment as s3deploy
)
import bin.override_rule as scan
from os import path

class S3AppCodeConst(core.Construct):

    @property
    def code_bucket(self):
        return self._code_bucket

    def __init__(self,scope: core.Construct, id: str, **kwargs,) -> None:
        super().__init__(scope, id, **kwargs)

       # Upload application code to S3 bucket 
        artifact_bucket=s3.Bucket(self, id, 
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            removal_policy=core.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            # server_access_logs_prefix="bucketAccessLog/",
            access_control = s3.BucketAccessControl.LOG_DELIVERY_WRITE
        )  
        code_path=path.dirname(path.abspath(__file__))
        s3deploy.BucketDeployment(self, "DeployCode",
            sources=[s3deploy.Source.asset(code_path+"/../../deployment/app_code")],
            destination_bucket= artifact_bucket,
            destination_key_prefix="app_code"
        )
        self._code_bucket = artifact_bucket.bucket_name
        
        # Override Cfn_Nag rule for S3 access logging
        scan.suppress_cfnNag_rule('W35','access logging stops the solution to be auto-deleted at user account. disable for now',artifact_bucket.node.default_child)

