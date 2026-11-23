"""AWS Lambda entry point for the CCD / ORU / TRN parsing service.

Accepts either inline base64-encoded documents or S3 object references,
runs them through the same parsing pipeline the local build scripts use,
and returns structured clinical JSON.

Payload-size note
-----------------
Lambda's synchronous invoke limit is 6 MB (request + response).  Callers
should batch documents **per QE** (one invoke per Qualified Entity) so
that neither the request payload nor the response body exceeds ~5.5 MB.
If the incoming event is larger than that, the handler returns a 413
without attempting to parse.

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
import sys
import base64
import logging
import traceback

from ccd_parser import parse_documents

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ~5.5 MB safety margin under Lambda's 6 MB synchronous invoke limit.
# Callers should batch per-QE so payloads stay well below this threshold.
MAX_PAYLOAD_BYTES = 5_500_000


def lambda_handler(event, context):
    """Lambda entry point."""
    try:
        # --- payload-size guard (Issue #4) ---
        # sys.getsizeof is a rough proxy for the serialised event; it errs
        # on the side of caution.  A json.dumps round-trip would be exact
        # but adds latency for large payloads.
        event_size = len(json.dumps(event))
        if event_size > MAX_PAYLOAD_BYTES:
            return {
                'statusCode': 413,
                'body': {
                    'error': 'PayloadTooLarge',
                    'message': (
                        f'Input event is ~{event_size / 1_000_000:.1f} MB, '
                        f'which exceeds the ~5.5 MB safety limit for Lambda '
                        f'synchronous invoke.  Batch documents per QE '
                        f'(one invoke per Qualified Entity) to stay under '
                        f'the 6 MB ceiling.'
                    ),
                }
            }

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
        # Log the full traceback to CloudWatch for debugging, but return
        # only a generic error type + message to the caller — no stack
        # frames, no internal file paths.
        logger.error("CCD parser failed: %s\n%s", e, traceback.format_exc())
        return {
            'statusCode': 500,
            'body': {
                'error': type(e).__name__,
                'message': 'An internal error occurred while parsing the documents. '
                           'Check CloudWatch logs for details.',
            }
        }
