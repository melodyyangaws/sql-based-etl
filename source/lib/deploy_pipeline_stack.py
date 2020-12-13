# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: MIT-0

from aws_cdk import (
    core,
    aws_iam as iam,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
)

class DeploymentPipeline(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Create IAM Role For CodeBuild
        codebuild_role = iam.Role(self, "BuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
            ]
        )

        # Create CodeBuild PipelineProject
        build_project = codebuild.PipelineProject(self, "BuildProject",
            role=codebuild_role,
            build_spec=codebuild.BuildSpec.from_source_filename("../../buildspec.yml"),
            environment=codebuild.BuildEnvironment(
                privileged=True,
            ),
            # pass env into the codebuild project so codebuild knows where to push
            environment_variables={
                'REGION': codebuild.BuildEnvironmentVariable(
                    value=self.region),
                'ACCOUNTNUMBER': codebuild.BuildEnvironmentVariable(
                    value=self.account)
            },
        )

        # Create CodePipeline
        pipeline = codepipeline.Pipeline(self, "Pipeline")

        # Create Artifact
        artifact = codepipeline.Artifact()

        # Add Source Stage
        pipeline.add_stage(
            stage_name="Source",
            actions=[
                codepipeline_actions.CodeCommitSourceAction(
                    action_name="SourceCodeRepo",
                    repository="sql-based-etl",
                    branch="master",
                    output=artifact
                )
            ]
        )

        # Add CodeBuild Stage
        pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="CodeBuildProject",
                    project=build_project,
                    type=codepipeline_actions.CodeBuildActionType.BUILD,
                    input=artifact
                )
            ]
        )