"""AWS Lambda entry point for the CCD / ORU / TRN parsing service.

Accepts either inline base64-encoded documents or S3 object references,
runs them through the same parsing pipeline the local build scripts use,
and returns structured clinical JSON.

Event formats
-------------
Inline mode::

    {
      "documents": {
        "ccds": ["<base64-encoded C-CDA XML>", ...],
        "orus": ["<base64-encoded HL7 v2 ORU>", ...],
        "trns": ["<base64-encoded C-CDA XML>", ...]
      }
    }

S3 mode::

    {
      "s3": {
        "bucket": "my-bucket",
        "ccd_keys": ["path/to/ccd1.xml", ...],
        "oru_keys": ["path/to/oru1.hl7", ...],
        "trn_keys": ["path/to/trn1.xml", ...]
      }
    }
"""
import json
import base64
import traceback

from ccd_parser import parse_documents


def lambda_handler(event, context):
    """Lambda entry point."""
    try:
        ccd_xmls = []
        oru_hl7s = []
        trn_xmls = []

        if 's3' in event:
            # Import boto3 only when needed — available in the Lambda runtime
            # but not necessarily on a local dev machine.
            import boto3
            s3 = boto3.client('s3')
            bucket = event['s3']['bucket']

            for key in event['s3'].get('ccd_keys', []):
                obj = s3.get_object(Bucket=bucket, Key=key)
                ccd_xmls.append(obj['Body'].read().decode('utf-8'))

            for key in event['s3'].get('oru_keys', []):
                obj = s3.get_object(Bucket=bucket, Key=key)
                oru_hl7s.append(obj['Body'].read().decode('utf-8'))

            for key in event['s3'].get('trn_keys', []):
                obj = s3.get_object(Bucket=bucket, Key=key)
                trn_xmls.append(obj['Body'].read().decode('utf-8'))

        elif 'documents' in event:
            docs = event['documents']
            ccd_xmls = [base64.b64decode(d).decode('utf-8') for d in docs.get('ccds', [])]
            oru_hl7s = [base64.b64decode(d).decode('utf-8') for d in docs.get('orus', [])]
            trn_xmls = [base64.b64decode(d).decode('utf-8') for d in docs.get('trns', [])]

        else:
            return {
                'statusCode': 400,
                'body': {'error': "Event must contain 's3' or 'documents' key"}
            }

        result = parse_documents(ccd_xmls, oru_hl7s, trn_xmls)

        return {
            'statusCode': 200,
            'body': result
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': {'error': str(e), 'trace': traceback.format_exc()}
        }
