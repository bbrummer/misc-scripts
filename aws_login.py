#!/bin/python
#
# Utility script to use get-session-token with MFA to create and save
# temporary credentials for use as a jump profile for MFA multi-account use
#
# Profiles needed       Default     Description
#   --login-profile     login       Valid, long lived Access Key credentials
#   --jump-profile      login-mfa   Temporary, MFA backed session credentials
#
#   <other>     - Any MFA profile that uses login-mfa as a source_profile
#
# BSD 2-Clause License
# 
# Copyright (c) 2018, Byron
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function
import boto3
from getpass import getpass
from subprocess import call
from pprint import pprint
import argparse

def main():
    args = get_args()

    # Get some details about our login profile.  This also verifies it's working
    sts_client  = boto3.session.Session(profile_name = args.login_profile).client('sts')
    login_arn   = sts_client.get_caller_identity()['Arn']
    jump_mfa    = login_arn.replace(':user/', ':mfa/')

    # Ask for the MFA token
    print("Using your '{}' profile and MFA to login to AWS".format(args.login_profile))
    mfa_token = getpass("Enter MFA code for {}: ".format(jump_mfa))

    # Get our temporary, MFA-flagged credentials
    temp_creds = sts_client.get_session_token(
        DurationSeconds = args.duration,
        SerialNumber    = jump_mfa,
        TokenCode       = mfa_token,
    )['Credentials']

    print("MFA login succeeded, saving your credentials to your '{}' profile.".format(args.jump_profile))
    print("Your AssumeRole profiles should use the directive 'source_profile = {}' to leverage this identity".format(args.jump_profile))

    # Save our MFA-flagged temporary credentials
    #
    # We shell out here to save our credentials because we know the user has
    # the AWS CLI installed and it knows better than we do where and how to
    # manage the ~/.aws/ files
    call(['aws', '--profile', args.jump_profile, 'configure', 'set', 'aws_access_key_id',       temp_creds['AccessKeyId']])
    call(['aws', '--profile', args.jump_profile, 'configure', 'set', 'aws_secret_access_key',   temp_creds['SecretAccessKey']])
    call(['aws', '--profile', args.jump_profile, 'configure', 'set', 'aws_session_token',       temp_creds['SessionToken']])

    # We're done, this is just some pretty output for the user and verifies
    # the jump profile
    print("Credentials saved.  Your temporary identity is:")
    temp_identity = boto3.session.Session(profile_name = args.jump_profile).client('sts').get_caller_identity()
    temp_identity.pop('ResponseMetadata') # Noise
    pprint(temp_identity, indent = 4)

def get_args():
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--login-profile', type=str, default="login")
    _parser.add_argument('--jump-profile',  type=str, default="login-mfa")
    _parser.add_argument('--duration',      type=int, default=43200)

    return _parser.parse_args()

if __name__ == "__main__":
    main()
