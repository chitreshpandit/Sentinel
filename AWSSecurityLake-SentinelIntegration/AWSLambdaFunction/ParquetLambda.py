import os
import io
import gzip
import json
import logging
import boto3
import time
import hashlib
import uuid
import random
import re
import tempfile
from datetime import datetime, timezone
from urllib.parse import unquote_plus
from azure.eventhub import EventHubProducerClient, EventData
from botocore.config import Config
import pyarrow.parquet as pq
import pandas as pd

# Logging setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SECRET_ARN = os.environ.get('SECRET_ARN')
BOTO3_CONFIG = Config(connect_timeout=5, read_timeout=5, retries={'max_attempts': 2})

# AWS Clients
s3_client = boto3.client('s3', config=BOTO3_CONFIG)
secrets_client = boto3.client('secretsmanager', config=BOTO3_CONFIG)

# Load secrets
secret_value = secrets_client.get_secret_value(SecretId=SECRET_ARN)
connection_string_map = json.loads(secret_value['SecretString'])


# Supported Parquet log types
LOG_TYPES = [
    'cloudfront',
    'LAMBDA_EXECUTION',
    'CLOUD_TRAIL_MGMT',
    'EKS_AUDIT',
    'ROUTE53',
    'S3_DATA',
    'SH_FINDINGS',
    'VPC_FLOW',
    'WAF',
]

# Init Event Hub producers
producers = {
    log_type: EventHubProducerClient.from_connection_string(connection_string_map[log_type])
    for log_type in LOG_TYPES if log_type in connection_string_map
}

eventhub_names = {
    log_type: producers[log_type].get_eventhub_properties()['eventhub_name']
    for log_type in producers
}

# Event Hub safe payload size (900 KB)
EVENTHUB_MAX_BYTES = 900 * 1024

# S3 metadata keys for deduplication
PROCESSED_METADATA_KEY = 'log-processor-status'
PROCESSING_METADATA_KEY = 'log-processor-processing'

# -------------------------------
# S3 Metadata-based Deduplication functions
# -------------------------------
def get_s3_object_metadata(bucket_name, object_key):
    """Get S3 object metadata"""
    try:
        response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        return response.get('Metadata', {})
    except Exception as e:
        logger.warning(f"Failed to get S3 metadata for {object_key}: {str(e)}")
        return {}

def is_file_already_processed(bucket_name, object_key):
    """Check if file has already been processed using S3 metadata"""
    try:
        metadata = get_s3_object_metadata(bucket_name, object_key)
        status = metadata.get(PROCESSED_METADATA_KEY)
        
        if status == 'completed':
            logger.info(f"File {object_key} already processed (status: {status})")
            return True
        elif status == 'processing':
            # Check if processing started more than 15 minutes ago (timeout)
            processing_time_str = metadata.get(PROCESSING_METADATA_KEY)
            if processing_time_str:
                try:
                    processing_time = datetime.fromisoformat(processing_time_str.replace('Z', '+00:00'))
                    if (datetime.now(timezone.utc) - processing_time.replace(tzinfo=None)).total_seconds() > 900:  # 15 minutes
                        logger.warning(f"File {object_key} processing timeout, allowing reprocessing")
                        return False
                    else:
                        logger.info(f"File {object_key} currently being processed")
                        return True
                except Exception as e:
                    logger.warning(f"Failed to parse processing time: {str(e)}")
                    return False
        return False
    except Exception as e:
        logger.warning(f"Failed to check processing status: {str(e)}")
        return False

def mark_file_as_processing(bucket_name, object_key, log_type):
    """Mark file as being processed using S3 metadata"""
    try:
        metadata = {
            PROCESSING_METADATA_KEY: datetime.now(timezone.utc).isoformat(),
            'log-processor-log-type': log_type,
            'log-processor-started': datetime.now(timezone.utc).isoformat()
        }
        
        s3_client.copy_object(
            Bucket=bucket_name,
            Key=object_key,
            CopySource={'Bucket': bucket_name, 'Key': object_key},
            Metadata=metadata,
            MetadataDirective='REPLACE'
        )
        logger.info(f"Marked file {object_key} as processing")
    except Exception as e:
        logger.error(f"Failed to mark file as processing: {str(e)}")

def mark_file_as_processed(bucket_name, object_key, log_type, status='completed'):
    """Mark file as processed using S3 metadata"""
    try:
        metadata = {
            PROCESSED_METADATA_KEY: status,
            'log-processor-log-type': log_type,
            'log-processor-completed': datetime.now(timezone.utc).isoformat(),
            'log-processor-batch-id': str(uuid.uuid4())
        }
        
        s3_client.copy_object(
            Bucket=bucket_name,
            Key=object_key,
            CopySource={'Bucket': bucket_name, 'Key': object_key},
            Metadata=metadata,
            MetadataDirective='REPLACE'
        )
        logger.info(f"Marked file {object_key} as {status}")
    except Exception as e:
        logger.error(f"Failed to mark file as processed: {str(e)}")

def generate_log_message_id(log_type, object_key, line_number, content_hash=None):
    """Generate unique ID for each log message"""
    if content_hash:
        return f"{log_type}:{object_key}:{line_number}:{content_hash}"
    else:
        # Generate hash from content if not provided
        content_hash = hashlib.md5(str(content_hash).encode()).hexdigest()[:8]
        return f"{log_type}:{object_key}:{line_number}:{content_hash}"

def enhance_log_with_metadata(log_line, log_type, object_key, line_number, batch_id):
    """Add metadata to log line for tracking and deduplication"""
    log_id = generate_log_message_id(log_type, object_key, line_number)
    
    # Create enhanced log entry with metadata
    enhanced_log = {
        "log_id": log_id,
        "batch_id": batch_id,
        "source": {
            "log_type": log_type,
            "object_key": object_key,
            "line_number": line_number
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original_log": log_line
    }
    
    return json.dumps(enhanced_log)

# -------------------------------
# Lambda handler
# -------------------------------
def lambda_handler(event, context):
    records = event.get('Records', [])
    if not records:
        logger.warning(f"No Records field found in event: {json.dumps(event)[:1000]}")
        return

    for record in records:
        s3_records = []

        # Case 1: Direct S3 trigger
        if 's3' in record:
            s3_records = [record]

        # Case 2: SQS trigger wrapping S3 event notifications (e.g., Security Lake)
        elif record.get('eventSource') == 'aws:sqs' or 'body' in record:
            body = record.get('body')
            if not body:
                logger.warning(f"SQS record missing body: {json.dumps(record)[:500]}")
                continue

            try:
                body_json = json.loads(body)
            except Exception as e:
                logger.error(f"Failed to parse SQS body as JSON: {str(e)}; body snippet: {body[:500]}")
                continue

            # Standard S3 event structure inside SQS body
            inner_records = body_json.get('Records', [])
            if not inner_records:
                logger.warning(f"No inner Records in SQS body JSON: {json.dumps(body_json)[:500]}")
                continue

            for inner in inner_records:
                if 's3' in inner:
                    s3_records.append(inner)

            if not s3_records:
                logger.warning(f"No S3 records found inside SQS message: {json.dumps(body_json)[:500]}")
                continue

        else:
            logger.warning(f"Skipping unsupported record type: {json.dumps(record)[:500]}")
            continue

        # Process all derived S3 records (whether direct or from SQS)
        for s3_info in s3_records:
            bucket_name = s3_info['s3']['bucket']['name']
            raw_key = s3_info['s3']['object']['key']
            # Security Lake and many S3 events URL-encode keys; decode before S3 API calls
            object_key = unquote_plus(raw_key)

            log_type = identify_log_type(object_key)
            if log_type not in LOG_TYPES:
                logger.warning(f"Unsupported log type for object {object_key}")
                continue

            # Check if file has already been processed using S3 metadata
            if is_file_already_processed(bucket_name, object_key):
                continue

            try:
                # Mark as processing to prevent concurrent processing
                mark_file_as_processing(bucket_name, object_key, log_type)
                
                # Process the S3 object
                process_s3_object(bucket_name, object_key, log_type)
                
                # Mark as completed
                mark_file_as_processed(bucket_name, object_key, log_type, 'completed')
                
            except Exception as e:
                # Mark as failed
                mark_file_as_processed(bucket_name, object_key, log_type, 'failed')
                logger.error(f"Failed to process {object_key}: {str(e)}")
                raise

# -------------------------------
# Identify log type
# -------------------------------
def identify_log_type(object_key):
    key_lower = object_key.lower()

    # Keep explicit CloudFront match (historically lowercase in LOG_TYPES/secrets)
    if "cloudfront" in key_lower:
        return "cloudfront"

    supported_upper = [
        "LAMBDA_EXECUTION",
        "CLOUD_TRAIL_MGMT",
        "EKS_AUDIT",
        "ROUTE53",
        "S3_DATA",
        "SH_FINDINGS",
        "VPC_FLOW",
        "WAF",
    ]

    for log_type in supported_upper:
        base = log_type.lower()
        variants = (base, base.replace("_", ""), base.replace("_", "-"))
        if any(v in key_lower for v in variants):
            return log_type

    return None

# -------------------------------
# Parquet support
# -------------------------------
def is_parquet_file(object_key):
    """Return True if the S3 object is in Parquet format (by key or common patterns)."""
    key_lower = object_key.lower()
    return key_lower.endswith('.parquet') or '.parquet' in key_lower


def parquet_to_ndjson_lines(parquet_bytes):
    """
    Read Parquet bytes and convert to NDJSON (one JSON object per line).
    Uses pyarrow; handles CloudFront and other Parquet log schemas.
    """
    # Legacy helper (loads entire file). Prefer streaming processing for large files.
    table = pq.read_table(io.BytesIO(parquet_bytes))
    lines = []
    for record in table.to_pylist():
        safe_record = {k: _to_json_safe(v) for k, v in record.items()} if isinstance(record, dict) else record
        lines.append(json.dumps(safe_record, default=str))
    return lines


def _to_json_safe(value):
    """Convert numpy/pandas scalars to native Python for JSON serialization."""
    if value is None:
        return None

    if isinstance(value, (list, tuple)):
        return [_to_json_safe(v) for v in value]

    if isinstance(value, dict):
        return {k: _to_json_safe(v) for k, v in value.items()}

    # Handle array-like values (numpy ndarray, pandas Series, etc.) before pd.isna.
    # pd.isna(array) returns a boolean array; using it in "if" causes ValueError.
    if hasattr(value, 'tolist') and not isinstance(value, (str, bytes, bytearray)):
        try:
            converted = value.tolist()
            if isinstance(converted, list):
                return [_to_json_safe(v) for v in converted]
            value = converted
        except Exception:
            pass

    # Only call pd.isna on scalar-like values; never use its result in "if" when it could be an array
    try:
        if getattr(value, 'size', 1) <= 1:
            missing = pd.isna(value)
            if isinstance(missing, bool):
                if missing:
                    return None
            elif hasattr(missing, 'all'):
                try:
                    if missing.all():
                        return None
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass

    if hasattr(value, 'item') and not hasattr(value, 'strftime'):  # numpy scalar, not datetime
        try:
            return value.item()
        except Exception:
            pass

    return value


def process_parquet_logs_complete_file(parquet_bytes, log_type, object_key):
    """
    Convert Parquet to NDJSON lines and send each row as a separate Event Hub event.
    """
    # Backward-compatible entrypoint: process the provided bytes in streaming batches.
    # (Still avoids pandas + avoids holding all rows as a list.)
    parquet_file = pq.ParquetFile(io.BytesIO(parquet_bytes))
    _process_parquet_parquetfile_in_batches(parquet_file, log_type, object_key)


# Canonical key for the only EKS unmapped entry we want to keep.
_UNMAPPED_EKS_CLUSTER_NAME_KEY = "eks_cluster_name"


def _filter_unmapped_keep_eks_cluster_name_only(obj):
    """
    For EKS Audit rows: keep only the first unmapped key/value pair whose key
    matches eks_cluster_name case-insensitively; remove all other unmapped entries.
    Returns a new dict; does not mutate the input.
    """
    if not isinstance(obj, dict) or "unmapped" not in obj:
        return obj

    unmapped = obj.get("unmapped")
    if not isinstance(unmapped, list):
        return obj

    cluster_name_entry = None
    for entry in unmapped:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue

        key_part = entry[0]
        if isinstance(key_part, str) and key_part.casefold() == _UNMAPPED_EKS_CLUSTER_NAME_KEY.casefold():
            cluster_name_entry = [_UNMAPPED_EKS_CLUSTER_NAME_KEY, entry[1]]
            break

    result = dict(obj)
    result["unmapped"] = [cluster_name_entry] if cluster_name_entry is not None else []
    return result


def _process_parquet_parquetfile_in_batches(parquet_file, log_type, object_key, batch_size=500):
    """
    Stream Parquet rows in batches to reduce memory usage.
    Each row becomes one Event Hub event; oversized rows are reduced (EKS unmapped filter) or truncated to EVENTHUB_MAX_BYTES.
    """
    batch_id = str(uuid.uuid4())
    rows_sent = 0
    oversized_rows = 0

    for batch_index, record_batch in enumerate(parquet_file.iter_batches(batch_size=batch_size)):
        rows = record_batch.to_pylist()
        payloads = []
        for row_index_in_batch, record in enumerate(rows):
            global_row_index = rows_sent + row_index_in_batch
            safe_record = {k: _to_json_safe(v) for k, v in record.items()} if isinstance(record, dict) else record

            if log_type == "EKS_AUDIT":
                safe_record = _filter_unmapped_keep_eks_cluster_name_only(safe_record)

            line = json.dumps(safe_record, default=str)

            payload_bytes = line.encode("utf-8")
            if len(payload_bytes) <= EVENTHUB_MAX_BYTES:
                payloads.append(line)
                continue

            oversized_rows += 1
            logger.error(
                f"Oversized Parquet row detected for {log_type} from {object_key} "
                f"(row_index={global_row_index}, size={len(payload_bytes)} bytes, limit={EVENTHUB_MAX_BYTES} bytes). "
                f"Attempting to reduce size."
            )

            # Fallback: byte truncate to limit.
            truncated_text = payload_bytes[:EVENTHUB_MAX_BYTES].decode("utf-8", errors="ignore")
            payloads.append(truncated_text)

        if payloads:
            send_to_eventhub(payloads, log_type, object_key, batch_id)
            rows_sent += len(rows)

    logger.info(
        f"Completed Parquet processing for {object_key} (log_type={log_type}, batch_id={batch_id}, "
        f"rows_sent={rows_sent}, oversized_rows={oversized_rows})."
    )


# -------------------------------
# Process S3 object
# -------------------------------
def process_s3_object(bucket_name, object_key, log_type):
    if is_parquet_file(object_key):
        # Stream download to disk to avoid holding large Parquet payloads in memory.
        key_lower = object_key.lower()
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            s3_client.download_fileobj(bucket_name, object_key, tmp)

        try:
            # Handle gzipped Parquet objects by suffix (with fallback for plain Parquet).
            if key_lower.endswith('.gz.parquet') or key_lower.endswith('.parquet.gz'):
                gz_path = tmp_path + ".gz"
                os.replace(tmp_path, gz_path)

                try:
                    with gzip.open(gz_path, "rb") as gz_in, tempfile.NamedTemporaryFile(delete=False) as out_tmp:
                        out_path = out_tmp.name
                        for chunk in iter(lambda: gz_in.read(1024 * 1024), b""):
                            out_tmp.write(chunk)

                    parquet_file = pq.ParquetFile(out_path)
                    _process_parquet_parquetfile_in_batches(parquet_file, log_type, object_key)
                    try:
                        os.remove(out_path)
                    except Exception:
                        pass
                except gzip.BadGzipFile:
                    # Suffix suggests gzip but content is plain Parquet (e.g. Security Lake naming).
                    logger.warning(
                        f"Parquet object {object_key} has gzip-like suffix but content is not gzip; processing as plain Parquet."
                    )
                    parquet_file = pq.ParquetFile(gz_path)
                    _process_parquet_parquetfile_in_batches(parquet_file, log_type, object_key)

                try:
                    os.remove(gz_path)
                except Exception:
                    pass
            else:
                parquet_file = pq.ParquetFile(tmp_path)
                _process_parquet_parquetfile_in_batches(parquet_file, log_type, object_key)
        finally:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            except Exception:
                pass
        return

    s3_obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)

    if object_key.endswith(".gz"):
        with gzip.GzipFile(fileobj=io.BytesIO(s3_obj['Body'].read())) as gz:
            content = gz.read().decode('utf-8')
    else:
        content = s3_obj['Body'].read().decode('utf-8')

    process_text_logs_complete_file(content, log_type, object_key)

# -------------------------------
# Split plain-text logs into chunks under Event Hub size limit
# -------------------------------
def process_text_logs_complete_file(content, log_type, object_key):
    lines = content.splitlines()
    if not lines:
        return

    # Generate a unique batch ID for this file processing (attached as Event Hub property)
    batch_id = str(uuid.uuid4())
    logger.info(f"Processing file {object_key} with batch_id: {batch_id}")

    header = lines[0]
    data_lines = lines[1:] if len(lines) > 1 else []

    buffer = [header]
    buffer_size = len((header + "\n").encode("utf-8"))
    chunks = []

    for line in data_lines:
        line_size = len((line + "\n").encode("utf-8"))
        if buffer_size + line_size > EVENTHUB_MAX_BYTES:
            chunks.append("\n".join(buffer))
            buffer = [header]
            buffer_size = len((header + "\n").encode("utf-8"))
        buffer.append(line)
        buffer_size += line_size

    if len(buffer) > 1:
        chunks.append("\n".join(buffer))

    send_to_eventhub(chunks, log_type, object_key, batch_id)

# -------------------------------
# Send to Event Hub
# -------------------------------
def send_to_eventhub(payloads, log_type, object_key, batch_id, max_retries=3, backoff_factor=2):
    if isinstance(payloads, str):
        payloads = [payloads]

    attempt = 0
    delay = 1

    def _extract_retry_after_seconds(exc: Exception):
        """
        Try to parse "Please wait X seconds" from Event Hubs throttling errors.
        Returns an int seconds or None.
        """
        try:
            msg = str(exc)
        except Exception:
            return None
        m = re.search(r"Please wait\s+(\d+)\s+seconds", msg)
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None

    while attempt < max_retries:
        try:
            # Build and flush batches as they fill up.
            event_data_batch = producers[log_type].create_batch()
            sent_count = 0

            for idx, payload in enumerate(payloads):
                payload_bytes = payload.encode("utf-8")
                if len(payload_bytes) > EVENTHUB_MAX_BYTES:
                    logger.error(
                        f"Oversized payload detected for {log_type} from {object_key} "
                        f"({len(payload_bytes)} bytes)."
                    )
                    continue

                event = EventData(payload)
                chunk_hash = hashlib.md5(payload_bytes).hexdigest()
                log_id = f"{log_type}:{object_key}:{idx}:{chunk_hash[:12]}"
                event.application_properties = {
                    'batch_id': batch_id,
                    'log_id': log_id,
                    'chunk_index': idx,
                    'object_key': object_key,
                    'log_type': log_type
                }

                try:
                    event_data_batch.add(event)
                except ValueError:
                    # Batch is full. Flush it and start a new batch, then retry once.
                    if sent_count == 0 and getattr(event_data_batch, "size_in_bytes", 0) == 0:
                        # Defensive: empty batch but can't add (should be rare). Treat as failure.
                        logger.error(
                            f"Failed to add payload to a fresh batch for {log_type} from {object_key}; "
                            f"payload size={len(payload_bytes)} bytes."
                        )
                        continue

                    producers[log_type].send_batch(event_data_batch)
                    sent_count += 1
                    event_data_batch = producers[log_type].create_batch()

                    try:
                        event_data_batch.add(event)
                    except ValueError:
                        logger.error(
                            f"Failed to add payload even after rotating batch for {log_type} from {object_key}; "
                            f"payload size={len(payload_bytes)} bytes."
                        )
                        continue

            # Flush remaining events in the final batch.
            try:
                # Only send if the batch has events; sending an empty batch can throw an exception.
                if getattr(event_data_batch, "size_in_bytes", 0) > 0:
                    producers[log_type].send_batch(event_data_batch)
                    sent_count += 1
            except Exception as e:
                logger.error(f"Failed to flush final batch for {log_type} from {object_key}: {str(e)}")
                raise

            logger.info(
                f"Sent {len(payloads)} {log_type} payloads from {object_key} "
                f"(batch_id: {batch_id}) to Event Hub '{eventhub_names[log_type]}'"
            )
            return

        except Exception as e:
            attempt += 1
            logger.error(f"Attempt {attempt} failed to send to Event Hub {log_type}: {str(e)}")
            if attempt < max_retries:
                # If Event Hubs tells us how long to wait (throttling), honor it.
                retry_after = _extract_retry_after_seconds(e)
                if retry_after is not None:
                    delay = max(delay, retry_after)

                # Add small jitter to reduce synchronized retries across concurrent invocations.
                jitter = random.uniform(0, 0.5)
                time.sleep(delay + jitter)
                delay *= backoff_factor
            else:
                error_msg = (
                    f"CRITICAL: Failed to send {log_type} logs from {object_key} "
                    f"to Event Hub '{eventhub_names[log_type]}' after {max_retries} attempts."
                )
                logger.error(error_msg)
                
                # Log detailed failure information
                logger.error(f"Failed batch details - batch_id: {batch_id}, attempts: {attempt}")
                raise Exception(error_msg)

def retry_failed_payloads(failed_payloads, log_type, object_key, batch_id):
    """Retry individual failed payloads"""
    for payload_info in failed_payloads:
        try:
            event_data_batch = producers[log_type].create_batch()
            event = EventData(payload_info['payload'])
            event.application_properties = {
                'batch_id': batch_id or 'unknown',
                'object_key': object_key,
                'log_type': log_type,
                'retry': 'true'
            }
            event_data_batch.add(event)
            producers[log_type].send_batch(event_data_batch)
            logger.info(f"Successfully retried individual payload from batch {batch_id}")
        except Exception as e:
            logger.error(f"Failed to retry individual payload from batch {batch_id}: {str(e)}")
            # This individual payload will be lost, but we've logged it