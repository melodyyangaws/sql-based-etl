######################################################################################################################
# Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                      #
#                                                                                                                   #
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
# with the License. A copy of the License is located at                                                             #
#                                                                                                                   #
#     http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                   #
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
# OR CONDITIONS OF ANY KIND, express o#implied. See the License for the specific language governing permissions     #
# and limitations under the License.  																				#                                                                              #
######################################################################################################################
import json
import logging
import os
import re
from fileinput import FileInput
from pathlib import Path
from typing import Dict, List

import jsii
from aws_cdk.core import (
    IStackSynthesizer,
    ISynthesisSession,
    DefaultStackSynthesizer,
)

logger = logging.getLogger("cdk-helper")

@jsii.implements(IStackSynthesizer)
class SolutionStackSubstitions(DefaultStackSynthesizer):
    """Used to handle AWS Solutions template substitutions and sanitization"""

    substitutions = None
    substitution_re = re.compile("%%[a-zA-Z-_][a-zA-Z-_]+%%")

    def _template_names(self, session: ISynthesisSession) -> List[Path]:
        assembly_output_path = Path(session.assembly.outdir)
        templates = [assembly_output_path.joinpath(self._stack.template_file)]

        # add this stack's children to the outputs to process (todo: this only works for singly-nested stacks)
        for child in self._stack.node.children:
            child_template = getattr(child, "template_file", None)
            if child_template:
                templates.append(assembly_output_path.joinpath(child_template))
        return templates

    def synthesize(self, session: ISynthesisSession):
        # when called with `cdk deploy` this outputs to cdk.out
        # when called from python directly, this outputs to a temporary directory
        result = DefaultStackSynthesizer.synthesize(self, session)

        asset_path_regional = self._stack.node.try_get_context(
            "SOLUTIONS_ASSETS_REGIONAL"
        )
        asset_path_global = self._stack.node.try_get_context("SOLUTIONS_ASSETS_GLOBAL")

        logger.info(
            f"solutions parameter substitution in {session.assembly.outdir} started"
        )
        for template in self._template_names(session):
            logger.info(f"substutiting parameters in {str(template)}")
            with FileInput(template, inplace=True) as template_lines:
                for line in template_lines:
                    # handle all template subsitutions in the line
                    for match in SolutionStackSubstitions.substitution_re.findall(line):
                        placeholder = match.replace("%", "")
                        replacement = self._stack.node.try_get_context(placeholder)
                        if not replacement:
                            raise ValueError(
                                f"Please provide a parameter substitution for {placeholder} via environment variable or CDK context"
                            )

                        line = line.replace(match, replacement)
                    # print the (now substituted) line in the context of template_lines
                    print(line, end="")
            logger.info(f"substituting parameters in {str(template)} completed")
        logger.info("solutions parameter substitution completed")

        # do not perform solution resource/ template cleanup if asset paths not passed
        if not asset_path_global or not asset_path_regional:
            return

        logger.info(
            f"solutions template customization in {session.assembly.outdir} started"
        )
        for template in self._templates(session):
            template.patch_lambda()
            template.patch_nested()
            template.delete_bootstrap_parameters()
            template.delete_cdk_helpers()
            template.save(
                asset_path_global=asset_path_global,
                asset_path_regional=asset_path_regional,
            )
        logger.info("solutions template customization completed")

        return result