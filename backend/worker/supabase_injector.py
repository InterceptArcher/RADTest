"""
Supabase data injection module.
Handles injecting raw JSON data into Supabase tables.
"""
import logging
from typing import Dict, Any, List
from supabase import create_client, Client
from datetime import datetime

logger = logging.getLogger(__name__)


class SupabaseInjector:
    """
    Handles injection of raw JSON data into Supabase tables.

    Tables:
    - raw-data: Raw JSON from intelligence sources
    - staging-normalized: Normalized data ready for validation
    - finalize-data: Validated and finalized data
    """

    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize Supabase client.

        Args:
            supabase_url: Supabase project URL (from environment)
            supabase_key: Supabase API key (from environment)

        Note:
            These values must be provided via environment variables.
        """
        self.client: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")

    async def inject_raw_data(
        self,
        company_name: str,
        domain: str,
        source: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Inject raw JSON data into the raw-data table.

        Args:
            company_name: Name of the company
            domain: Company domain
            source: Data source name (apollo, pdl, etc.)
            data: Raw JSON data from the source

        Returns:
            Dictionary with injection status and record ID

        Raises:
            Exception: If injection fails
        """
        try:
            record = {
                "company_name": company_name,
                "domain": domain,
                "source": source,
                "raw_data": data,
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending"
            }

            logger.info(
                f"Injecting raw data for {company_name} from {source}"
            )

            result = self.client.table("raw-data").insert(record).execute()

            logger.info(
                f"Successfully injected raw data. Record ID: {result.data[0]['id']}"
            )

            return {
                "success": True,
                "record_id": result.data[0]["id"],
                "source": source
            }

        except Exception as e:
            logger.error(f"Failed to inject raw data: {e}")
            raise

    async def inject_batch_raw_data(
        self,
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Inject multiple raw data records in a single batch operation.

        Args:
            records: List of record dictionaries

        Returns:
            Dictionary with batch injection results

        Raises:
            Exception: If batch injection fails
        """
        try:
            # Add timestamps and status to all records
            for record in records:
                record["created_at"] = datetime.utcnow().isoformat()
                record["status"] = "pending"

            logger.info(f"Batch injecting {len(records)} raw data records")

            result = self.client.table("raw-data").insert(records).execute()

            logger.info(
                f"Successfully batch injected {len(result.data)} records"
            )

            return {
                "success": True,
                "record_count": len(result.data),
                "record_ids": [r["id"] for r in result.data]
            }

        except Exception as e:
            logger.error(f"Failed to batch inject raw data: {e}")
            raise

    async def get_staging_data(
        self,
        limit: int = 100,
        status: str = "pending"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve data from staging-normalized table for validation.

        Args:
            limit: Maximum number of records to retrieve
            status: Filter by status (pending, validated, failed)

        Returns:
            List of staging records
        """
        try:
            result = self.client.table("staging-normalized")\
                .select("*")\
                .eq("status", status)\
                .limit(limit)\
                .execute()

            logger.info(
                f"Retrieved {len(result.data)} records from staging-normalized"
            )

            return result.data

        except Exception as e:
            logger.error(f"Failed to retrieve staging data: {e}")
            raise

    async def inject_finalized_data(
        self,
        company_name: str,
        domain: str,
        validated_data: Dict[str, Any],
        confidence_score: float,
        validation_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Inject validated and finalized data into finalize-data table.

        Args:
            company_name: Name of the company
            domain: Company domain
            validated_data: Validated and cleaned data
            confidence_score: Confidence score from validation
            validation_metadata: Metadata from validation process

        Returns:
            Dictionary with injection status and record ID

        Raises:
            Exception: If injection fails
        """
        try:
            record = {
                "company_name": company_name,
                "domain": domain,
                "validated_data": validated_data,
                "confidence_score": confidence_score,
                "validation_metadata": validation_metadata,
                "created_at": datetime.utcnow().isoformat(),
                "status": "finalized"
            }

            logger.info(
                f"Injecting finalized data for {company_name} "
                f"(confidence: {confidence_score})"
            )

            result = self.client.table("finalize-data").insert(record).execute()

            logger.info(
                f"Successfully injected finalized data. "
                f"Record ID: {result.data[0]['id']}"
            )

            return {
                "success": True,
                "record_id": result.data[0]["id"],
                "confidence_score": confidence_score
            }

        except Exception as e:
            logger.error(f"Failed to inject finalized data: {e}")
            raise

    async def update_record_status(
        self,
        table_name: str,
        record_id: str,
        status: str,
        error_message: str = None
    ) -> Dict[str, Any]:
        """
        Update the status of a record in any table.

        Args:
            table_name: Name of the table
            record_id: ID of the record to update
            status: New status value
            error_message: Optional error message if status is 'failed'

        Returns:
            Dictionary with update status

        Raises:
            Exception: If update fails
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }

            if error_message:
                update_data["error_message"] = error_message

            result = self.client.table(table_name)\
                .update(update_data)\
                .eq("id", record_id)\
                .execute()

            logger.info(
                f"Updated record {record_id} status to {status} in {table_name}"
            )

            return {
                "success": True,
                "record_id": record_id,
                "status": status
            }

        except Exception as e:
            logger.error(f"Failed to update record status: {e}")
            raise
